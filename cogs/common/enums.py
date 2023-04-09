from enum import Enum


class FixtureFormat(str, Enum):
    BO2 = 'BO2'
    BO3 = 'BO3'
    BO5 = 'BO5'
    BO3CTF = 'CTF BO3'
    BO5CTF = 'CTF BO5'
    BO3TS = 'TS BO3'
    BO5TS = 'TS BO5'
    BO3UTWC =  'UTWC BO3'
    BO5UTWC =  'UTWC BO5'
    BO2TSONLY = 'TS BO2'
    BO2CTFONLY = 'CTF BO2'

class FixtureTitle(str, Enum):
    Null =  'None'
    QuarterFinals = 'Quarter Finals'
    SemiFinals =  'Semi Finals'
    BronzeFinal = 'Bronze Final'
    Final =  'Final'

class RosterStatus(Enum):
    Invited = 0
    Member = 1
    Captain = 2
    Inactive = 3

class FixtureStatus(Enum):
    Created = 0
    Scheduled = 1
    InProgress = 2
    Finished = 3
    ScoresEntered = 4
    Archived = 5

class Gamemode(str, Enum):
    TS = 'TS'
    CTF = 'CTF'