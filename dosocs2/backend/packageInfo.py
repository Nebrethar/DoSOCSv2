
import json
import re
import subprocess
import os


def license():
    print("LICENSE INFO")
    return "OK"

def retrieve_package_information(owner, repo):
    print("PULLING")
    repo_url = 'https://github.com/' + owner + '/' + repo + '.git'

    cwd = os.path.dirname(os.path.realpath(__file__))

    temp = open("temp.txt", "r+")
    subprocess.call(['sudo', 'git', 'clone', repo_url, cwd + '/repodl/' + repo], shell=False)
    pope = subprocess.Popen(['sudo', 'dosocs2', 'oneshot', cwd + '/repodl/' + repo, '-T' + cwd + '/package.tag'], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.call(['sudo', 'dosocs2', 'oneshot', cwd + '/repodl/' + repo], shell=False, stdout=temp)
    out, err = pope.communicate()
    if out:
        print(out.decode('UTF-8'))
    if err:
         print(err.decode('UTF-8'))
    results_f = re.findall(r'(SPDXVersion): (.*)\n(DataLicense): (.*)\n(DocumentNamespace): (.*)\n(DocumentName): (.*)\n(SPDXID): (.*)\n(DocumentComment): (.*|)\n', out.decode('UTF-8'))
    results = re.findall(r'(PackageName): (.*)\n(SPDXID): (.*)\n(PackageVersion|):? ?(.*|)\n?(PackageFileName): (.*)\n(PackageSupplier): (.*)\n(PackageOriginator): (.*)\n(PackageDownloadLocation): (.*)\n(PackageVerificationCode): (.*)\n(PackageChecksum|):? ?(.*|)\n?(PackageHomePage): (.*)\n(PackageLicenseConcluded): (.*)\n*(PackageLicenseDeclared): (.*)\n(PackageLicenseComments): (.*)\n(PackageCopyrightText): (.*)\n(PackageSummary): (.*)\n(PackageDescription): (.*)\n(PackageComment): (.*|)', out.decode('UTF-8'))
    results_l = re.findall(r'(PackageLicenseInfoFromFiles): (.*)\n?', out.decode('UTF-8')),
    results_c = re.findall(r'(Creator): (.*)\n(Created): (.*)\n(CreatorComment): (.*|)\n(LicenseListVersion): (.*)', out.decode('UTF-8'))
    results_s = re.findall(r'\n(LicenseID): (.*[^\s]*)\n(LicenseName): (.*[^s])\n(ExtractedText): b\'(.*[^s])\'\n(LicenseCrossReference): (.*)\n(LicenseComment): (.*[^s])', out.decode('UTF-8'))

    print(results_s)
    license_information = []
    #print('\n')
    #print(results_l)
    #print('\n')
    temp = {}
    c = 0
    for i in range(0, 6):
        c = i*2
        temp[results_f[0][c]] = results_f[0][c+1]

    license_information.append(temp)
    temp = {}
    g = 0
    for i in range(0, 4):
        g = i*2
        temp[results_c[0][g]] = results_c[0][g+1]

    license_information.append(temp)
    temp = {}
    for i in range(0, 17):
        j = i*2
        if (results[0][j]):
            temp[results[0][j]] = results[0][j+1]

    license_information.append(temp)

    temp_l = {}
    i = 0
    for i in range(0, len(results_l[0])):
        temp_l["License " + str(i)] = results_l[0][i][1]
        i += 1
    #print(temp_l)
    license_information.append(temp_l)

    temp = {}
    for i in range(0, len(results_s)):
            temp[results_s[i][0]] = results_s[i][1]
            temp[results_s[i][2]] = results_s[i][3]
            temp[results_s[i][4]] = results_s[i][5]
            temp[results_s[i][6]] = results_s[i][7]
            temp[results_s[i][8]] = results_s[i][9]
            license_information.append(temp)
    #dfinal = dict(temp)
    #dfinal.update(temp_l)
    return json.dumps(license_information)
