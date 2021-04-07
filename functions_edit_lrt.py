import csv, os, gzip, logging, shutil, re, time

import phonenumbers
from lxml import etree
from datetime import date, datetime
from pyfiglet import Figlet
from tqdm import tqdm

from functions_socks import create_sftp_connection, create_ssh_connection
from constants import (
    CARRIERS,
    DDI_FILE,
    SN_FILE,
    HISTORY_PATH,
    DATA_ARAMIS,
    VSR_NAME,
    VSRS,
    WORKING_PATH,
    BACKUP_PATH,
    REMOTE_PATH,
)


def create_custom_logger(logger_name, log_path):

    current_date_time = datetime.now()
    logname = logger_name + "_{}.log".format(
        current_date_time.strftime("%d%m%Y_%H%M%S")
    )

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    log_format = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s : %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S GMT%z",
    )
    log_file = os.path.join(log_path, logname)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)
    return logger, log_file


def read_csv(file):
    with open(file, "r") as f:
        reader = list(csv.reader(f, delimiter="\t"))
    return reader


def is_csv(file):
    if file.endswith(".csv"):
        return file
    else:
        msg = file + " is not a valid *.csv file"
        raise argparse.ArgumentTypeError(msg)


def gunzip_lrt(input_file, logger_name):
    output_file = input_file.rstrip(".gz")
    with gzip.open(input_file, "rt") as fin:
        with open(output_file, "w") as fout:
            fout.write(fin.read())
    logger_name.info(
        "Successfully gunzip file {} to file {}".format(input_file, output_file)
    )
    os.remove(input_file)
    return output_file


def gzip_lrt(input_file, logger_name):
    output_file = input_file + ".gz"
    with open(input_file, "r") as fin:
        with gzip.open(output_file, "wt") as fout:
            fout.write(fin.read())
    logger_name.info(
        "Successfully gzip file {} to file {}".format(input_file, output_file)
    )
    os.remove(input_file)
    return output_file


def download_lrt(host, l_path, r_path, lrts, logger_name):
    mysftp, mytransport = create_sftp_connection(host)
    mysftp.chdir(r_path)
    fails = 0
    for lrt in tqdm(lrts, desc="Downloading LRT(s)", leave=False):
        r_file = r_path + "/" + lrt
        l_file = l_path + "\\" + lrt
        try:
            mysftp.get(r_file, l_file)
        except IOError:
            logger_name.info(f"LRT {lrt} not found.")
            fails += 1
        else:
            logger_name.info(f"Successfully downloaded LRT: {lrt}")
    mysftp.close()
    mytransport.close()
    return fails


def upload_lrt(host, l_path, r_path, lrts, logger_name):
    mysftp, mytransport = create_sftp_connection(host)
    mysftp.chdir(r_path)
    for lrt in tqdm(lrts, desc="Uploading LRT(s)", leave=False):
        r_file = r_path + "/" + lrt
        l_file = l_path + "\\" + lrt
        mysftp.put(l_file, r_file)
        logger_name.info(f"Successfully uploaded LRT: {lrt}")
    mysftp.close()
    mytransport.close()


def generate_lrt_R(lrt_file, csv_file, domain, logger_name):
    tree = etree.parse(lrt_file)
    root = tree.getroot()
    logger_name.info(f"Total entries: {len(root)}")
    count = 0
    for row in tqdm(csv_file, desc="Adding entries", leave=False):
        number, tgrp, fqdn = row[0], row[1], row[2]
        route_elem = etree.SubElement(root, "route")
        user_elem = etree.SubElement(route_elem, "user")
        next_elem = etree.SubElement(route_elem, "next")
        user_elem.set("type", "E164")
        next_elem.set("type", "regex")
        user_elem.text = number
        next_elem.text = f"!(^.*)$!sip:\\1;tgrp={tgrp};trunk-context={domain}@{fqdn}!"
        count += 1
        time.sleep(0.05)

    etree.indent(tree)
    xml_data = etree.tostring(
        tree,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )

    with open(lrt_file, "wb") as f:
        f.write(xml_data)

    logger_name.info(f"Entries added: {count}")
    logger_name.info(f"New total entries: {len(root)}")


def generate_lrt_S(lrt_file, csv_file, logger_name):
    tree = etree.parse(lrt_file)
    root = tree.getroot()
    logger_name.info(f"Total entries: {len(root)}")
    count = 0
    for row in tqdm(csv_file, desc="Adding entries", leave=False):
        number, tgrp, as_cluster = row[0], row[3], row[4]
        route_elem = etree.SubElement(root, "route")
        user_elem = etree.SubElement(route_elem, "user")
        next_elem = etree.SubElement(route_elem, "next")
        user_elem.set("type", "E164")
        next_elem.set("type", "regex")
        user_elem.text = number
        next_elem.text = f"!(^.*)$!sip:\\1;key={tgrp}@{as_cluster}Cluster!"
        count += 1
        time.sleep(0.05)

    etree.indent(tree)
    xml_data = etree.tostring(
        tree,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )

    with open(lrt_file, "wb") as f:
        f.write(xml_data)

    logger_name.info(f"Entries added: {count}")
    logger_name.info(f"New total entries: {len(root)}")


def generate_lrt_B(lrt_file, csv_file, logger_name):
    tree = etree.parse(lrt_file)
    root = tree.getroot()
    logger_name.info(f"Total entries: {len(root)}")
    count = 0
    for row in tqdm(csv_file, desc="Adding entries", leave=False):
        number = row[0]
        lst_carrier = CARRIERS.get(row[5])
        tgrp, tcontext, fqdn = lst_carrier[0], lst_carrier[1], lst_carrier[2]
        route_elem = etree.SubElement(root, "route")
        user_elem = etree.SubElement(route_elem, "user")
        next_elem = etree.SubElement(route_elem, "next")
        user_elem.set("type", "E164")
        next_elem.set("type", "regex")
        user_elem.text = number
        next_elem.text = f"!(^.*)$!sip:\\1;tgrp={tgrp};trunk-context={tcontext}@{fqdn}!"
        count += 1
        time.sleep(0.05)

    etree.indent(tree)
    xml_data = etree.tostring(
        tree,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
        standalone=True,
    )

    with open(lrt_file, "wb") as f:
        f.write(xml_data)

    logger_name.info(f"Entries added: {count}")
    logger_name.info(f"New total entries: {len(root)}")


def remove_file_by_extension(dir, exten):
    for f in os.listdir(dir):
        if f.endswith(exten):
            os.remove(os.path.join(dir, f))


def count_lines_csv(input_file):
    lines = 0
    for row in open(input_file):
        lines += 1
    return lines


def refresh_lrt(host, lrts, logger_name):
    myssh = create_ssh_connection(host)
    channel = myssh.invoke_shell()
    output = ""
    for lrt in tqdm(lrts, desc="Refreshing LRTs", leave=False):
        channel.send(f"notify lrtd refresh {lrt}" + "\n")
        time.sleep(2)
        resp = channel.recv(4096).decode("ascii")
        output += resp
    lines = output.split("\r\n")
    command_list = [line for line in lines if re.search("notify", line)]
    result_list = [line for line in lines if re.search("routes", line)]
    for i in range(0, len(lrts)):
        logger_name.info(f"{command_list[i]}: {result_list[i]}")
    myssh.close()


def edit_lrt_vsr(domain, input_file, vsrs, tables, logger_name):
    for vsr_name in tqdm(vsrs, desc="Working in VSR(s)", colour="green"):
        remove_file_by_extension(WORKING_PATH, ".gz")
        logger_name.info(f"Working in {vsr_name}")
        vsr_ip = VSRS.get(vsr_name)
        lst_lrt_refresh = [x + f".{domain}" for x in tables]
        lst_lrt = [x + f".{domain}.xml.gz" for x in tables]
        fails = download_lrt(vsr_ip, WORKING_PATH, REMOTE_PATH, lst_lrt, logger_name)
        if fails:
            logger_name.info(f"Work in {vsr_name} aborted")
            continue
        else:
            for tab in tqdm(tables, desc="Working in tables", leave=False):
                logger_name.info(f"Start the work in table {tab}.{domain}.xml")
                lrt = os.path.join(WORKING_PATH, f"{tab}.{domain}.xml.gz")
                lrt_bk = os.path.join(
                    BACKUP_PATH,
                    f"{tab}.{domain}-{vsr_name}-{datetime.now().strftime('%d%m%Y_%H%M%S')}.xml.gz",
                )
                shutil.copyfile(lrt, lrt_bk)
                logger_name.info(f"Backup completed from {lrt} to {lrt_bk}")
                lrt_1 = gunzip_lrt(lrt, logger_name)
                if tab == "R":
                    generate_lrt_R(lrt_1, input_file, domain, logger_name)
                elif tab == "S":
                    generate_lrt_S(lrt_1, input_file, logger_name)
                elif tab == "B":
                    generate_lrt_B(lrt_1, input_file, logger_name)
                lrt_2 = gzip_lrt(lrt_1, logger_name)
                logger_name.info(f"Finish the work in table {tab}.{domain}.xml")
            upload_lrt(vsr_ip, WORKING_PATH, REMOTE_PATH, lst_lrt, logger_name)
            refresh_lrt(vsr_ip, lst_lrt_refresh, logger_name)
        logger_name.info(f"Finish the work in {vsr_name}")
    return fails


def save_output_file(input_file, logger_name):
    current_date_time = datetime.now().strftime("%d%m%Y_%H%M%S")
    file_record = input_file.rstrip(".csv") + f"_{current_date_time}" + ".csv"
    filename = os.path.join(HISTORY_PATH, file_record)
    shutil.copyfile(input_file, filename)
    logger_name.info(f"History file generated: {file_record}")


def get_data_aramis(phone):
    x = phonenumbers.parse(f"+{phone}", None)
    cc = str(x.country_code)
    result = DATA_ARAMIS.get(cc)
    return result, cc


def create_file_DDI(input_file, enterpise, logger_name):
    total_lines = count_lines_csv(input_file)
    with open(DDI_FILE, "w", newline="") as final:
        with open(input_file, newline="") as original:
            reader = csv.reader(
                original,
                delimiter="\t",
            )
            writer = csv.writer(final, quoting=csv.QUOTE_ALL, delimiter=",")
            writer.writerow(
                [
                    "Source ID",
                    "Source",
                    "ISO Code",
                    "Country",
                    "Digits",
                    "Last Modification",
                    "Source Type",
                    "Mask",
                    "Mask Active",
                    "CPC",
                    "NumA",
                    "Group Country NumA",
                    "Business Unit",
                    "MNC",
                    "Rate",
                    "Billing Increments",
                ]
            )
            counter = 0
            with tqdm(
                desc="Generating DDI file", total=total_lines, colour="green"
            ) as pbar:
                for rows in reader:
                    data, cc = get_data_aramis(rows[0])
                    writer.writerow(
                        [
                            data[0],
                            "DDI-Bidirectional",
                            cc,
                            data[1],
                            rows[0],
                            "",
                            "Fixed",
                            rows[0],
                            "1",
                            "0",
                            "",
                            "",
                            "",
                            enterpise,
                            "0,0",
                            "1/1",
                        ]
                    )
                    counter += 1
                    pbar.update(1)
                    time.sleep(0.1)
    logger_name.info(f"Successfully generated: {DDI_FILE}")
    logger_name.info(f"The {DDI_FILE} has {counter} entries")


def create_file_SN(input_file, enterpise, logger_name):
    total_lines = count_lines_csv(input_file)
    with open(SN_FILE, "w", newline="") as final:
        with open(input_file, newline="") as original:
            reader = csv.reader(
                original,
                delimiter="\t",
            )
            writer = csv.writer(final, quoting=csv.QUOTE_ALL, delimiter=",")
            writer.writerow(
                [
                    "Source ID",
                    "Source",
                    "ISO Code",
                    "Country",
                    "Digits",
                    "Last Modification",
                    "Source Type",
                    "Mask",
                    "Mask Active",
                    "CPC",
                    "NumA",
                    "Group Country NumA",
                    "Business Unit",
                    "MNC",
                    "Rate",
                    "Billing Increments",
                ]
            )
            counter = 0
            with tqdm(
                desc="Generating Special Number file", total=total_lines, colour="green"
            ) as pbar:
                for rows in reader:
                    data, cc = get_data_aramis(rows[0])
                    writer.writerow(
                        [
                            data[0],
                            "Special-Numbers",
                            cc,
                            data[1],
                            rows[3],
                            "",
                            "Fixed",
                            rows[0],
                            "1",
                            "0",
                            "",
                            "",
                            "",
                            enterpise,
                            "0,0",
                            "1/1",
                        ]
                    )
                    if row[4]:
                        writer.writerow(
                            [
                                data[0],
                                "Special-Numbers",
                                cc,
                                data[1],
                                rows[4],
                                "",
                                "Mobile",
                                rows[0],
                                "1",
                                "0",
                                "",
                                "",
                                "",
                                enterpise,
                                "0,0",
                                "1/1",
                            ]
                        )
                    counter += 1
                    pbar.update(1)
                    time.sleep(0.1)
    logger_name.info(f"Successfully generated: {SN_FILE}")
    logger_name.info(f"The {SN_FILE} has {counter} entries")


def print_menu():
    f = Figlet(font="slant")
    print(f.renderText("Daily Tasks"))
    print(23 * "-", " MENU ", 23 * "-")
    print("[1] Configure LRT(s)")
    print("[2] Generate DDI-Bidirectional file")
    print("[3] Conf LRT & Gen DDI-Bid")
    print("[q] Exit")
    print(54 * "-")
    while True:
        choice = input("Select the task: ").lower()
        if choice in ["1", "2", "3", "q"]:
            return choice
        else:
            print("Please enter a valid option")
            continue


def input_values_option1():
    while True:
        domain = input("Ingress the customer's domain: ").replace(" ", "")
        if domain != "":
            break
        else:
            print("Enter a valid domain")
            continue

    while True:
        tables = input("Ingress the name of the LRTs: ").upper().split()
        if all(item in ["R", "S", "B"] for item in tables):
            break
        else:
            print("Enter a valid value (R, S or B)")
            continue

    while True:
        vsrs = input("Ingress the VSRs where to configure the LRTs: ").lower().split()
        if all(item in VSR_NAME for item in vsrs):
            break
        else:
            print("Enter a valid VSR hostname")
            continue
    return domain, tables, vsrs


def input_values_option2():
    while True:
        customer = input("Ingress the ENTERPRISE for the customer: ").replace(" ", "")
        if customer != "":
            break
        else:
            print("Enter a valid ENTERPRISE name")
            continue
    return customer


def input_values_option4():
    while True:
        customer = input("Ingress the ENTERPRISE for the customer: ").replace(" ", "")
        if customer != "":
            break
        else:
            print("Enter a valid ENTERPRISE name")
            continue

    while True:
        domain = input("Ingress the customer's domain: ").replace(" ", "")
        if domain != "":
            break
        else:
            print("Enter a valid domain")
            continue

    while True:
        vsrs = input("Ingress the VSRs where to configure the LRTs: ").lower().split()
        if all(item in VSR_NAME for item in vsrs):
            break
        else:
            print("Enter a valid VSR hostname")
            continue

    return customer, domain, vsrs