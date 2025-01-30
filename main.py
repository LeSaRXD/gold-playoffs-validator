from dataclasses import dataclass
import asyncio
import aiohttp


CURRENT_SEASON = 7


@dataclass
class PlayerData:
	lowest: int
	highest: int
	elo: int


async def player_season_data(client: aiohttp.ClientSession, username: str, season: int) -> tuple[PlayerData | None, str | None]:
	async with client.get(f"https://mcsrranked.com/api/users/{username}?season={season}") as res:
		json: dict = await res.json()
		data = json.get("data", None)

		if data is None:
			return (None, f"Request error: data is None\n{json}")

		if json["status"] != "success":
			return (None, f"API error: {data}")

		try:
			current: int | None = data["eloRate"]
			highest: int | None = data["seasonResult"]["highest"]
			lowest: int | None = data["seasonResult"]["lowest"]

		except KeyError as e:
			return (None, str(e))

		if any((lowest is None, highest is None, current is None)):
			return (None, "Stats error: highest, lowest or current ELO is None")

		return (PlayerData(lowest, highest, current), None)


async def player_data(client: aiohttp.ClientSession, username: str) -> tuple[str, PlayerData | None, str | None]:
	(curr_data, err) = await player_season_data(client, username, CURRENT_SEASON)
	if err is not None:
		return (username, None, err)

	prev_seasons = [player_season_data(client, username, season) for season in range(0, CURRENT_SEASON)]
	prev_datas: list[tuple[PlayerData | None, str | None]] = await asyncio.gather(*prev_seasons)

	highest_total = curr_data.highest
	for season, (prev, err) in enumerate(prev_datas):
		if err is not None:
			print(f"Season {season} error\n{err}")
		else:
			highest_total = max(highest_total, prev.highest)
	
	return (username, PlayerData(curr_data.lowest, highest_total, curr_data.elo), None)


async def main() -> None:
	with open("output.csv", "w") as fout:
		fout.write("Name,Current Elo,Highest of all time,Current season lowest\n")

	usernames = []
	with open("names.txt", "r") as fin:
		usernames = [line.strip() for line in fin.readlines() if len(line.strip()) > 0]

	async with aiohttp.ClientSession() as session:
		for name in usernames:
			assert all(ch.isalnum() or ch == "_" for ch in name), f"Invalid username '{name}'"

		tasks = [player_data(session, username) for username in usernames]
		results = await asyncio.gather(*tasks)

		for (username, data, err) in results:
			if err is not None:
				print(f"Could not get user {username}\n{err}")
				continue

			with open("output.csv", "a") as fout:
				fout.write(f"{username},{data.elo},{data.highest},{data.lowest}\n")

	print("Done! Check output.csv")


if __name__ == "__main__":
	asyncio.run(main())
