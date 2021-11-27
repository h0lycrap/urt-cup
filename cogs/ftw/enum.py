from enum import Enum


class UserTeamRoles(str, Enum):
    leader = 'leader'
    captain = 'captain'
    member = 'member'
    inactive = 'inactive'
    invited = 'invited'


class MatchType(str, Enum):
    group = 'group'
    playoff = 'playoff'
    grand_final = 'grand_final'
    silver_final = 'silver_final'


class GameTypes(int, Enum):
    team_survivor = 4
    capture_the_flag = 7
