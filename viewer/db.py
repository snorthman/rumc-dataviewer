import sys

this = sys.modules[__name__]

this.patients = []
this.dir = ''


def initialize(json):
    this.patients = json['patients'] if 'patients' in json else []
    this.dir = json['dir'] if 'dir' in json else ''