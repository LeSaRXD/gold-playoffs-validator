from dataclasses import dataclass
import asyncio
import aiohttp


CURRENT_SEASON = 7


@dataclass
class PlayerData:
	lowest: int | None
	highest: int | None
	elo: int | None
	average_time: int | None
	best_time: int | None

	def __str__(self):
		return f"{self.elo},{self.highest},{self.lowest},{self.average_elo},{self.best_elo}"

	@property
	def average_elo(self) -> int | None:
		return int(299.1976737976074 / (self.average_time * 1e-6 - 0.4035017788410187) + 695.6695914268494)

	@property
	def best_elo(self) -> int | None:
		return int(196.40617072582245 / (self.best_time * 1e-6 - 0.2820969820022583) + 760.9823942184448)


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
			stats = data["statistics"]["season"]
			best_time: int | None = stats["bestTime"]["ranked"]
			total_time: int | None = stats["completionTime"]["ranked"]
			total_matches: int | None = stats["completions"]["ranked"]
			average_time: float | None = None
			if total_time is not None and total_matches not in (0, None):
				average_time = total_time / total_matches
		except KeyError as e:
			return (None, f"KeyError: {str(e)}")


		return (PlayerData(lowest, highest, current, average_time, best_time), None)


async def player_data(client: aiohttp.ClientSession, username: str) -> tuple[str, PlayerData | None, str | None]:
	(curr_data, err) = await player_season_data(client, username, CURRENT_SEASON)
	if err is not None:
		return (username, None, err)

	if not all((curr_data.average_time, curr_data.best_time, curr_data.elo, curr_data.highest, curr_data.lowest)):
		return (username, None, "Some of stats in the current season is None")

	prev_seasons = [player_season_data(client, username, season) for season in range(0, CURRENT_SEASON)]
	prev_datas: list[tuple[PlayerData | None, str | None]] = await asyncio.gather(*prev_seasons)

	highest_total = curr_data.highest
	for season, (prev, err) in enumerate(prev_datas):
		if err is not None:
			print(f"Season {season} error\n{err}")
		elif prev.highest is None:
			continue
		else:
			highest_total = max(highest_total, prev.highest)
	
	curr_data.highest = highest_total

	return (username, curr_data, None)


async def main() -> None:
	fout = open("output.csv", "w")
	fout.write("Name,Current Elo,Highest of all time,Current season lowest,Average time pred,Best time pred\n")

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

			print(f"Got user {username}: {repr(data)}")
			fout.write(f"{username},{str(data)}\n")

	print("Done! Check output.csv")


def tests():
	test_data = PlayerData(None, None, None, 945_000, 732_000)
	assert test_data.average_elo == 1248, "Average time elo prediction is wrong"
	assert test_data.best_elo == 1197, "Best time elo prediction is wrong"


if __name__ == "__main__":
	tests()
	asyncio.run(main())
