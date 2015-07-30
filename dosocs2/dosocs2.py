#!/usr/bin/env python2

# <SPDX-License-Identifier: Apache-2.0>
# Copyright (c) 2014-2015 University of Nebraska at Omaha (UNO) and other
# contributors.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''Usage:
{0} configtest [-f FILE]
{0} dbinit [-f FILE] [--no-confirm]
{0} generate [-C COMMENT] [-f FILE] [-N NAME] (PACKAGE-ID)
{0} newconfig
{0} oneshot [-c COMMENT] [-C COMMENT] [-f FILE] [-n NAME] [-N NAME]
    [-s SCANNERS] [-r VER] (PATH)
{0} print [-f FILE] (DOC-ID)
{0} scan [-c COMMENT] [-f FILE] [-n NAME] [-r VER] [-s SCANNERS] (PATH)
{0} scanners [-f FILE]
{0} (--help | --version)

Commands:
  configtest    Check configuration
  dbinit        Create tables, views, and initial config file
                  (destructive, will prompt first)
  generate      Generate SPDX document data in the database for a
                  particular package
  newconfig     Create a copy of the default configuration at
                  $XDG_CONFIG_HOME/dosocs2/dosocs2.conf
                  (overwrite existing config)
  oneshot       Scan, generate document, and print document in one
                  command
  print         Render and print a document to standard output
  scan          Scan an archive file or directory
  scanners      List available scanners

Options:
  -C, --doc-comment=COMMENT   Comment for new document (otherwise use empty
                                string)
  -c, --package-comment=COMMENT
                              Comment for new package (otherwise use empty
                                string)
  -f, --config=FILE           Alternate config file
  -N, --doc-name=NAME         Name for new document (otherwise create name
                                from package name)
  -n, --package-name=NAME     Name for new package (otherwise create
                                name from filename)
  -r, --package-version=VER   Version string for new package (otherwise use
                                empty string)
  -s, --scanners=SCANNERS     Comma-separated list of scanners to use
                                ('dosocs2 scanners' to see choices)
      --no-confirm            Don't prompt before initializing database with
                                'dbinit' (dangerous!)

Report bugs to <tgurney@unomaha.edu>.
'''

from __future__ import print_function

import os
import pkg_resources
import sys

import docopt

from . import config
from . import dbinit
from . import render
from . import scanners
from . import schema as db
from . import spdxdb
from . import util


format_map = {
    'tag': pkg_resources.resource_filename('dosocs2', 'templates/2.0.tag'),
}

__version__ = '0.9.0'


def msg(text, **kwargs):
    print('dosocs2' + ': ' + text, **kwargs)
    sys.stdout.flush()


def errmsg(text, **kwargs):
    print('dosocs2' + ': ' + text, file=sys.stderr, **kwargs)
    sys.stdout.flush()


def do_scan(engine, package_root, package_file_path=None, selected_scanners=None,
            package_name=None, package_version='', package_comment=''):
    if selected_scanners is None:
        selected_scanners = ()
    kwargs = {
        'name': package_name,
        'version': package_version,
        'comment': package_comment,
        'package_root': package_root,
        'package_file_path': package_file_path,
        }
    with engine.begin() as conn:
        package = spdxdb.register_package(conn, **kwargs)
    errmsg('{}: package_id: {}'.format(package_file_path or package_root, package['package_id']))
    for scanner in selected_scanners:
        errmsg('running {} on package {}'.format(scanner.name, package['package_id']))
        scanner_kwargs = {
            'package_id': package['package_id'],
            'package_root': package_root,
            'package_file_path': package_file_path
            }
        with engine.begin() as conn:
            scanner_inst = scanner(conn)
            scanner_inst.run(**scanner_kwargs)
    return package


def main():
    argv = docopt.docopt(doc=__doc__.format(os.path.basename(sys.argv[0])), version=__version__)
    alt_config = argv['--config']
    engine = db.initialize(config.config['dosocs2']['connection_uri'], util.bool_from_str(config.config['dosocs2']['echo']))
    doc_id = argv['DOC-ID']
    package_id = argv['PACKAGE-ID']
    package_path = argv['PATH']
    new_doc_comment = argv['--doc-comment'] or ''
    new_doc_name = argv['--doc-name'] or argv['--package-name']

    if argv['--config']:
        try:
            os.stat(alt_config)
        except EnvironmentError as ex:
            errmsg('{}: {}'.format(alt_config, ex.strerror))
            sys.exit(1)
        config.update_config(alt_config)
    if not argv['--scanners']:
        argv['--scanners'] = config.config['dosocs2']['default_scanners']
    selected_scanners = []
    for this_scanner_name in argv['--scanners'].split(','):
        try:
            this_scanner = scanners.scanners[this_scanner_name]
        except KeyError:
            errmsg("'{}' is not a known scanner".format(this_scanner_name))
            sys.exit(1)
        if this_scanner not in selected_scanners:
            selected_scanners.append(this_scanner)

    if argv['configtest']:
        print('\n' + 79 * '-' + '\n')
        print('Config at: {}'.format(config.config_location(alt_config)))
        print('\n' + 79 * '-' + '\n')
        print('Effective configuration:\n')
        print('# begin dosocs2 config')
        config.dump_to_file(sys.stdout)
        print('# end dosocs2 config')
        print('\n' + 79 * '-' + '\n')
        print('Testing database connection...', end='')
        sys.stdout.flush()
        with engine.begin() as conn:
            conn.execute('select 1;')
        print('ok.')
        sys.exit(0)

    elif argv['newconfig']:
        config_path = config.DOSOCS2_CONFIG_PATH
        configresult = config.create_user_config()
        if not configresult:
            errmsg('failed to write config file to {}'.format(config_path))
        else:
            msg('wrote config file to {}'.format(config_path))
        sys.exit(0 if configresult else 1)

    elif argv['scanners']:
        default_scanners = config.config['dosocs2']['default_scanners'].split(',')
        for s in sorted(scanners.scanners):
            if s in default_scanners:
                print(s + ' [default]')
            else:
                print(s)
        sys.exit(0)

    elif argv['dbinit']:
        if not argv['--no-confirm']:
            errmsg('preparing to initialize the database')
            errmsg('all existing data will be deleted!')
            errmsg('make sure you are connected to the internet before continuing.')
            errmsg('type the word "YES" (all uppercase) to commit.')
            answer = raw_input()
            if answer != 'YES':
                errmsg('canceling operation.')
                sys.exit(1)
        sys.exit(0 if dbinit.initialize(__version__) else 1)

    elif argv['print']:
        with engine.begin() as conn:
            if spdxdb.fetch(conn, db.documents, doc_id) is None:
                errmsg('document id {} not found in the database.'.format(doc_id))
                sys.exit(1)
            print(render.render_document(conn, doc_id, format_map['tag']))

    elif argv['generate']:
        kwargs = {
            'name': new_doc_name,
            'comment': new_doc_comment
            }
        with engine.begin() as conn:
            package = spdxdb.fetch(conn, db.packages, package_id)
            if package is None:
                errmsg('package id {} not found in the database.'.format(package_id))
                sys.exit(1)
            document_id = spdxdb.create_document(conn, package, **kwargs)['document_id']
        fmt = '(package_id {}): document_id: {}\n'
        sys.stderr.write(fmt.format(package_id, document_id))

    elif argv['scan']:
        kwargs = {
            'engine': engine,
            'selected_scanners': selected_scanners,
            'package_name': argv['--package-name'],
            'package_version': argv['--package-version'],
            'package_comment': argv['--package-comment']
            }
        if os.path.isfile(package_path):
            with util.tempextract(package_path) as (tempdir, _):
                kwargs['package_root'] = tempdir
                kwargs['package_file_path'] = package_path
                do_scan(**kwargs)
        else:
            kwargs['package_root'] = package_path
            kwargs['package_file_path'] = None
            do_scan(**kwargs)


    elif argv['oneshot']:
        kwargs = {
            'engine': engine,
            'selected_scanners': selected_scanners,
            'package_name': argv['--package-name'],
            'package_version': argv['--package-version'],
            'package_comment': argv['--package-comment']
            }
        if os.path.isfile(package_path):
            with util.tempextract(package_path) as (tempdir, _):
                kwargs['package_root'] = tempdir
                kwargs['package_file_path'] = package_path
                package = do_scan(**kwargs)
        else:
            kwargs['package_root'] = package_path
            kwargs['package_file_path'] = None
            package = do_scan(**kwargs)
        for scanner in selected_scanners:
            sys.stderr.write(scanner.name + '\n')
            with engine.begin() as conn:
                scanner_inst = scanner(conn)
                scanner_inst.run(package['package_id'], package_path)
        with engine.begin() as conn:
            document = spdxdb.get_doc_by_package_id(conn, package_id)
            if document:
                doc_id = document['document_id']
            else:
                kwargs = {
                    'name': new_doc_name,
                    'comment': new_doc_comment
                    }
                doc_id = spdxdb.create_document(conn, package, **kwargs)['document_id']
            fmt = '{}: document_id: {}\n'
            sys.stderr.write(fmt.format(package_path, doc_id))
        with engine.begin() as conn:
            print(render.render_document(conn, doc_id, format_map['tag']))


if __name__ == "__main__":
    main()
