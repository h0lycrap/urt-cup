import datetime
import os
from typing import List

import aiohttp

from cogs.ftw.enum import UserTeamRoles, MatchType, GameTypes


class FTWClient:
    def __init__(self):
        self.ftw_host = os.getenv("FTW_HOST") or "https://dev.ftwgl.net"
        self.ftw_api_key = os.getenv("FTW_API_KEY")

        if self.ftw_api_key is None:
            raise EnvironmentError("FTW_API_KEY not set")

    async def cup_create(self, name: str, abbreviation: str, playoff_length: int,
                         start_date: datetime, roster_lock_date: datetime) -> int:
        request_body = {
            'name': name,
            'abbreviation': abbreviation,
            'playoff_length': playoff_length,
            'start_date': start_date,
            'roster_lock_date': roster_lock_date,
        }
        async with aiohttp.ClientSession() as session:
            session.headers.add("Authorization", f"Bearer {self.ftw_api_key}")
            async with session.post(f"{self.ftw_host}/api/v1/cup", json=request_body) as resp:
                resp_body = await resp.json()
                if resp.status != 200:
                    print(f"Failed ({resp.status}) to create cup")
                    print(resp_body)
                else:
                    cup_id = resp_body['cup_id']
                    return cup_id

    async def user_create(self, discord_id: int, discord_username: str, urt_auth: str):
        request_body = {
            'discord_id': discord_id,
            'discord_username': discord_username,
            'urt_auth': urt_auth
        }
        async with aiohttp.ClientSession() as session:
            session.headers.add("Authorization", f"Bearer {self.ftw_api_key}")
            async with session.post(f"{self.ftw_host}/api/v1/user", json=request_body) as resp:
                if resp.status != 200:
                    print(f"Failed ({resp.status}) to create user", request_body)
                    print(await resp.json())

    async def team_create(self, creator_discord_id: int, team_name: str, team_tag: str) -> int:
        request_body = {
            'creator_discord_id': creator_discord_id,
            'name': team_name,
            'tag': team_tag
        }
        async with aiohttp.ClientSession() as session:
            session.headers.add("Authorization", f"Bearer {self.ftw_api_key}")
            async with session.post(f"{self.ftw_host}/api/v1/team", json=request_body) as resp:
                resp_body = await resp.json()
                if resp.status != 200:
                    print(f"Failed ({resp.status}) to create team", request_body)
                    print(resp_body)
                else:
                    team_id = resp_body['team_id']
                    return team_id

    async def team_join_cup(self, team_id: int, cup_id: int):
        request_body = {
            'team_id': team_id,
            'cup_id': cup_id
        }
        async with aiohttp.ClientSession() as session:
            session.headers.add("Authorization", f"Bearer {self.ftw_api_key}")
            async with session.post(f"{self.ftw_host}/api/v1/cup/team", json=request_body) as resp:
                if resp.status != 200:
                    print(f"Failed ({resp.status}) to create team", request_body)
                    print(await resp.json())

    async def cup_team_division(self, cup_id: int, team_id: int, division: int):
        request_body = {
            'cup_id': cup_id,
            'team_id': team_id,
            'division': division
        }
        async with aiohttp.ClientSession() as session:
            session.headers.add("Authorization", f"Bearer {self.ftw_api_key}")
            async with session.put(f"{self.ftw_host}/api/v1/cup/team/division", json=request_body) as resp:
                if resp.status != 200:
                    print(f"Failed ({resp.status}) to create team", request_body)
                    print(await resp.json())

    async def team_add_user(self, team_id: int, discord_id: int, role: UserTeamRoles):
        request_body = {
            'team_id': team_id,
            'discord_id': discord_id,
            'role': role.value
        }
        async with aiohttp.ClientSession() as session:
            session.headers.add("Authorization", f"Bearer {self.ftw_api_key}")
            async with session.post(f"{self.ftw_host}/api/v1/team/user/join", json=request_body) as resp:
                if resp.status != 200:
                    print(f"Failed ({resp.status}) to create team", request_body)
                    print(await resp.json())

    async def team_remove_user(self, team_id: int, discord_id: int):
        request_body = {
            'team_id': team_id,
            'discord_id': discord_id
        }
        async with aiohttp.ClientSession() as session:
            session.headers.add("Authorization", f"Bearer {self.ftw_api_key}")
            async with session.post(f"{self.ftw_host}/api/v1/team/user/quit", json=request_body) as resp:
                if resp.status != 200:
                    print(f"Failed to remove {discord_id} from {team_id}")
                    print(await resp.json())

    async def match_create(self, league_id: int, team_ids: List[int], best_of: int, round: int,
                           match_type: MatchType, match_date: datetime) -> int:
        request_body = {
            'league_id': league_id,
            'team_ids': team_ids,
            'best_of': best_of,
            'round': round,
            'match_type': match_type.value,
            'match_date': match_date
        }

        async with aiohttp.ClientSession() as session:
            session.headers.add("Authorization", f"Bearer {self.ftw_api_key}")
            async with session.post(f"{self.ftw_host}/api/v1/team/user/quit", json=request_body) as resp:
                resp_body = await resp.json()
                if resp.status != 200:
                    print(f"Failed to create match")
                    print(resp_body)
                else:
                    match_id = resp_body['match_id']
                    return match_id

    async def server_locations(self):
        async with aiohttp.ClientSession() as session:
            session.headers.add("Authorization", f"Bearer {self.ftw_api_key}")
            async with session.get(f"{self.ftw_host}/api/v1/rent/locations") as resp:
                if resp.status == 200:
                    return await resp.json()

    async def server_active(self):
        async with aiohttp.ClientSession() as session:
            session.headers.add("Authorization", f"Bearer {self.ftw_api_key}")
            async with session.get(f"{self.ftw_host}/api/v1/rent/active") as resp:
                if resp.status == 200:
                    return await resp.json()

    # Server will likely take a couple of minutes to boot, so use the returned
    async def server_rent(self, match_id: int, dcid: int, gametype: GameTypes, rcon: str, password: str, ttl_hours: int) -> int:
        request_body = {
            'match_id': match_id,
            'dcid': dcid,
            'gametype': gametype.value,
            'rcon': rcon,
            'password': password,
            'ttl_hours': ttl_hours
        }
        async with aiohttp.ClientSession() as session:
            session.headers.add("Authorization", f"Bearer {self.ftw_api_key}")
            async with session.post(f"{self.ftw_host}/api/v1/rent/match", json=request_body) as resp:
                resp_body = await resp.json()
                if resp.status != 200:
                    print(f"Failed to rent server for match")
                    print(resp_body)
                else:
                    server_id = resp_body['id']
                    return server_id
