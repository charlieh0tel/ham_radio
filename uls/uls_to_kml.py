#!/usr/bin/python3

import csv
import dataclasses
import sys

import fastkml

# Reference:
#
# http://data.fcc.gov/download/license-view/fcc-license-view-data-dictionary.doc


@dataclasses.dataclass(kw_only=True)
class ULSRecord:
    callsign: str
    fullname: str
    first: str
    middle: str
    last: str
    address: str
    city: str
    state: str
    zipcode: str
    frn: str

    @staticmethod
    def MakeRecord(parts):
        return ULSRecord(
            callsign=parts[4],
            fullname=parts[7],
            first=parts[8],
            middle=parts[9],
            last=parts[10],
            address=parts[15],
            city=parts[16],
            state=parts[17],
            zipcode=parts[18],
            frn=parts[22],
        )


def ParseULSRecords(csvfile):
    reader = csv.reader(csvfile, delimiter="|", quotechar="'")
    records = []
    for record in reader:
        if record[0] == "EN":
            records.append(ULSRecord.MakeRecord(record))
    return records


def CreateKMLFromRecords(records):
    k = fastkml.kml.KML()
    ns = "{http://www.opengis.net/kml/2.2}"

    d = fastkml.kml.Document(ns, "docid", "ULS Records")
    k.append(d)

    for record in records:
        p = fastkml.kml.Placemark(ns, record.callsign, record.callsign)
        p.address = f"{record.address} {record.city} {record.state} {record.zipcode}"
        d.append(p)

    return k.to_string(prettyprint=True)


def main(argv):
    records = ParseULSRecords(sys.stdin)
    print(CreateKMLFromRecords(records))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
