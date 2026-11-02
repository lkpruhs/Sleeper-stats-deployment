import requests
import sys

class SleeperClient:
    BASE_URL = "https://api.sleeper.app/v1"

    def __init__(self):
        self.session = requests.Session()

    def _get(self, endpoint):
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from {url}: {e}")
            return None

    def get_league_info(self, league_id):
        return self._get(f"league/{league_id}")

    def get_users(self, league_id):
        return self._get(f"league/{league_id}/users")

    def get_rosters(self, league_id):
        return self._get(f"league/{league_id}/rosters")

    def get_matchups(self, league_id, week):
        return self._get(f"league/{league_id}/matchups/{week}")

    def get_team_mapping(self, league_id):
        users = self.get_users(league_id)
        rosters = self.get_rosters(league_id)
        
        if not users or not rosters:
            return {}

        user_map = {user['user_id']: user['display_name'] for user in users}
        
        roster_map = {}
        for roster in rosters:
            owner_id = roster.get('owner_id')
            roster_id = roster.get('roster_id')
            if owner_id and roster_id:
                roster_map[roster_id] = user_map.get(owner_id, "Unknown Manager")
                
        return roster_map

def main():
    if len(sys.argv) < 2:
        print("Error: Please provide a League ID.")
        sys.exit(1)
        
    current_league_id = sys.argv[1] 
    client = SleeperClient()

    print("Fetching league history...")
    
    all_performances = []
    active_id = current_league_id

    while active_id:
        league_info = client.get_league_info(active_id)
        
        if not league_info:
            print(f"Could not load data for league ID {active_id}. Stopping history search.")
            break
            
        season_year = league_info.get('season', 'Unknown')
        league_name = league_info.get('name', 'Unknown League')
        
        print(f"Processing Year: {season_year} - {league_name}")
        
        team_mapping = client.get_team_mapping(active_id)
        
        for week in range(1, 19):
            matchups = client.get_matchups(active_id, week)
            
            if not matchups:
                continue 
                
            games = {}
            for team_data in matchups:
                matchup_id = team_data.get('matchup_id')
                if matchup_id not in games:
                    games[matchup_id] = []
                games[matchup_id].append(team_data)

            for matchup_id, teams in games.items():
                if len(teams) == 2:
                    t1, t2 = teams[0], teams[1]
                    
                    t1_name = team_mapping.get(t1['roster_id'], f"Team {t1['roster_id']}")
                    t2_name = team_mapping.get(t2['roster_id'], f"Team {t2['roster_id']}")
                    
                    t1_points = t1.get('points')
                    t1_score = float(t1_points) if t1_points is not None else 0.0
                
                    t2_points = t2.get('points')
                    t2_score = float(t2_points) if t2_points is not None else 0.0
                    
                    all_performances.append({
                        'year': season_year,
                        'week': week,
                        'team': t1_name,
                        'score': t1_score,
                        'opponent': t2_name,
                        'opp_score': t2_score
                    })
                    
                    all_performances.append({
                        'year': season_year,
                        'week': week,
                        'team': t2_name,
                        'score': t2_score,
                        'opponent': t1_name,
                        'opp_score': t1_score
                    })

        active_id = league_info.get('previous_league_id')
        
        if active_id == "0" or not active_id:
            break

    if not all_performances:
        print("\nNo matchup data found.")
        return

    # Sort for Highest 20
    sorted_desc = sorted(all_performances, key=lambda x: x['score'], reverse=True)
    top_20 = sorted_desc[:20]

    # Sort for Lowest 20 (filtering out exact 0.0s to avoid unplayed/abandoned games)
    valid_scores = [p for p in all_performances if p['score'] > 0]
    sorted_asc = sorted(valid_scores, key=lambda x: x['score'])
    bottom_20 = sorted_asc[:20]

    # --- Tally Appearances ---
    team_summary = {}
    
    def init_team(t):
        if t not in team_summary:
            team_summary[t] = {'high': 0, 'high_opp': 0, 'low': 0, 'low_opp': 0}

    for perf in top_20:
        team, opp = perf['team'], perf['opponent']
        init_team(team)
        init_team(opp)
        team_summary[team]['high'] += 1
        team_summary[opp]['high_opp'] += 1

    for perf in bottom_20:
        team, opp = perf['team'], perf['opponent']
        init_team(team)
        init_team(opp)
        team_summary[team]['low'] += 1
        team_summary[opp]['low_opp'] += 1

    sorted_summary = sorted(
        team_summary.items(), 
        key=lambda x: (x[1]['high'], x[1]['low']), 
        reverse=True
    )

    # --- Generate Dark Mode HTML Output ---
    print("\nGenerating HTML file...")
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sleeper Fantasy Score Records</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #121212; color: #e0e0e0; }
            h2 { text-align: center; color: #ffffff; margin-top: 50px; }
            table { width: 85%; margin: 20px auto; border-collapse: collapse; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5); background-color: #1e1e1e; }
            th, td { padding: 15px; text-align: center; border-bottom: 1px solid #333; }
            th { background-color: #00d287; color: #121212; text-transform: uppercase; font-size: 14px; letter-spacing: 0.05em; font-weight: bold; }
            tr:hover { background-color: #2a2a2a; }
            .score-high { font-weight: bold; color: #00d287; }
            .score-low { font-weight: bold; color: #ff5555; }
            .summary-table th { background-color: #2c2c2c; color: #00d287; }
        </style>
    </head>
    <body>
        <h2>Team Appearances in Records</h2>
        <table class="summary-table">
            <thead>
                <tr>
                    <th>Team</th>
                    <th>Times with Top Score</th>
                    <th>Times as Opponent (Top)</th>
                    <th>Times with Lowest Score</th>
                    <th>Times as Opponent (Lowest)</th>
                </tr>
            </thead>
            <tbody>
    """

    for team, stats in sorted_summary:
        html_content += f"""
                <tr>
                    <td>{team}</td>
                    <td>{stats['high']}</td>
                    <td>{stats['high_opp']}</td>
                    <td>{stats['low']}</td>
                    <td>{stats['low_opp']}</td>
                </tr>
        """

    html_content += """
            </tbody>
        </table>

        <h2>Top 20 Highest Weekly Scores (All-Time)</h2>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Year</th>
                    <th>Week</th>
                    <th>Team</th>
                    <th>Score</th>
                    <th>Opponent</th>
                    <th>Opp Score</th>
                </tr>
            </thead>
            <tbody>
    """

    for rank, perf in enumerate(top_20, 1):
        html_content += f"""
                <tr>
                    <td>{rank}</td>
                    <td>{perf['year']}</td>
                    <td>{perf['week']}</td>
                    <td>{perf['team']}</td>
                    <td class="score-high">{perf['score']:.2f}</td>
                    <td>{perf['opponent']}</td>
                    <td>{perf['opp_score']:.2f}</td>
                </tr>
        """

    html_content += """
            </tbody>
        </table>

        <h2>Top 20 Lowest Weekly Scores (All-Time)</h2>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Year</th>
                    <th>Week</th>
                    <th>Team</th>
                    <th>Score</th>
                    <th>Opponent</th>
                    <th>Opp Score</th>
                </tr>
            </thead>
            <tbody>
    """

    for rank, perf in enumerate(bottom_20, 1):
        html_content += f"""
                <tr>
                    <td>{rank}</td>
                    <td>{perf['year']}</td>
                    <td>{perf['week']}</td>
                    <td>{perf['team']}</td>
                    <td class="score-low">{perf['score']:.2f}</td>
                    <td>{perf['opponent']}</td>
                    <td>{perf['opp_score']:.2f}</td>
                </tr>
        """

    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """

    with open("top_20_scores.html", "w", encoding="utf-8") as file:
        file.write(html_content)

    print("Success! The results have been saved to 'top_20_scores.html'.")

if __name__ == "__main__":
    main()
