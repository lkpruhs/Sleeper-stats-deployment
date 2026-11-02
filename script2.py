import requests
import itertools
import sys

class SleeperClient:
    BASE_URL = "https://api.sleeper.app/v1"

    def __init__(self):
        self.session = requests.Session()
        self.players_cache = None

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

    def get_transactions(self, league_id, week):
        return self._get(f"league/{league_id}/transactions/{week}")

    def get_all_players(self):
        if not self.players_cache:
            print("Downloading NFL players dataset (this may take a few seconds)...")
            self.players_cache = self._get("players/nfl")
        return self.players_cache

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

def get_gradient_color(value, max_value):
    if max_value == 0 or value == 0:
        return "hsl(0, 100%, 25%)"
    
    hue = (value / max_value) * 120
    return f"hsl({hue}, 75%, 35%)"

def main():
    if len(sys.argv) < 2:
        print("Error: Please provide a League ID.")
        sys.exit(1)
        
    current_league_id = sys.argv[1]
    client = SleeperClient()
    players_data = client.get_all_players() or {}

    print("Fetching league transaction history...")
    
    trade_counts = {}
    trade_matrix = {}
    managers_set = set()
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
        
        for manager in team_mapping.values():
            managers_set.add(manager)
            if manager not in trade_matrix:
                trade_matrix[manager] = {}
            if manager not in trade_counts:
                trade_counts[manager] = 0

        for week in range(1, 19):
            transactions = client.get_transactions(active_id, week)
            
            if not transactions:
                continue 
                
            for tx in transactions:
                if tx.get('type') == 'trade' and tx.get('status') == 'complete':
                    roster_ids = tx.get('roster_ids', [])
                    involved_managers = [team_mapping.get(r_id, f"Team {r_id}") for r_id in roster_ids]
                    
                    for manager in involved_managers:
                        trade_counts[manager] += 1

                    trade_summary = f"<b>{season_year} Week {week}:</b><br>"
                    
                    adds = tx.get('adds') or {}
                    for player_id, roster_id in adds.items():
                        receiving_manager = team_mapping.get(roster_id, f"Team {roster_id}")
                        player_info = players_data.get(player_id, {})
                        player_name = f"{player_info.get('first_name', '')} {player_info.get('last_name', player_id)}".strip()
                        trade_summary += f"- {receiving_manager} received {player_name}<br>"
                        
                    draft_picks = tx.get('draft_picks') or []
                    for pick in draft_picks:
                        receiving_manager = team_mapping.get(pick['owner_id'], f"Team {pick['owner_id']}")
                        season = pick.get('season')
                        round_num = pick.get('round')
                        trade_summary += f"- {receiving_manager} received {season} Round {round_num} pick<br>"

                    for m1, m2 in itertools.combinations(involved_managers, 2):
                        if m2 not in trade_matrix[m1]: trade_matrix[m1][m2] = {'count': 0, 'details': []}
                        if m1 not in trade_matrix[m2]: trade_matrix[m2][m1] = {'count': 0, 'details': []}
                        
                        trade_matrix[m1][m2]['count'] += 1
                        trade_matrix[m1][m2]['details'].append(trade_summary)
                        
                        trade_matrix[m2][m1]['count'] += 1
                        trade_matrix[m2][m1]['details'].append(trade_summary)

        active_id = league_info.get('previous_league_id')
        
        if active_id == "0" or not active_id:
            break

    if not trade_counts:
        print("\nNo trade data found. Please double-check your initial league_id.")
        return

    sorted_trades = sorted(trade_counts.items(), key=lambda x: x[1], reverse=True)
    all_managers = sorted(list(managers_set))
    
    max_matrix_trades = 0
    for m1 in trade_matrix:
        for m2, data in trade_matrix[m1].items():
            if data['count'] > max_matrix_trades:
                max_matrix_trades = data['count']

    print("\nGenerating HTML file...")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>All-Time Trade Counts</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #121212; color: #e0e0e0; }}
            h2 {{ text-align: center; color: #ffffff; margin-top: 40px; }}
            table {{ width: 90%; margin: 20px auto; border-collapse: collapse; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5); background-color: #1e1e1e; }}
            th, td {{ padding: 12px; text-align: center; border: 1px solid #333; }}
            th {{ background-color: #2c2c2c; color: #ffffff; font-size: 14px; }}
            tr:hover {{ background-color: #2a2a2a; }}
            .score {{ font-weight: bold; color: #00d287; }}
            .matrix-table th {{ background-color: #1c1c1c; position: sticky; top: 0; z-index: 2; }}
            .matrix-cell {{ font-weight: bold; color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); position: relative; cursor: pointer; }}
            .matrix-diagonal {{ background-color: #121212; }}
            
            /* Tooltip CSS */
            .matrix-cell .tooltiptext {{
                visibility: hidden;
                width: 320px;
                background-color: #2c2c2c;
                color: #e0e0e0;
                text-align: left;
                padding: 10px;
                border-radius: 6px;
                border: 1px solid #555;
                position: absolute;
                z-index: 10;
                bottom: 110%;
                left: 50%;
                margin-left: -160px;
                opacity: 0;
                transition: opacity 0.2s;
                font-weight: normal;
                text-shadow: none;
                font-size: 12px;
                max-height: 250px;
                overflow-y: auto;
                box-shadow: 0 4px 12px rgba(0,0,0,0.8);
            }}
            .matrix-cell:hover .tooltiptext {{
                visibility: visible;
                opacity: 1;
            }}
        </style>
    </head>
    <body>
        <h2>All-Time Trades Per Manager</h2>
        <table style="width: 60%;">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Manager</th>
                    <th>Completed Trades</th>
                </tr>
            </thead>
            <tbody>
    """

    for rank, (manager, count) in enumerate(sorted_trades, 1):
        html_content += f"""
                <tr>
                    <td>{rank}</td>
                    <td>{manager}</td>
                    <td class="score">{count}</td>
                </tr>
        """

    html_content += """
            </tbody>
        </table>

        <h2>Team-to-Team Trade Checkerboard</h2>
        <table class="matrix-table">
            <thead>
                <tr>
                    <th>Manager</th>
    """
    
    for m in all_managers:
        html_content += f"<th>{m}</th>"
    html_content += "</tr></thead><tbody>"

    for m1 in all_managers:
        html_content += f"<tr><th>{m1}</th>"
        for m2 in all_managers:
            if m1 == m2:
                html_content += "<td class='matrix-diagonal'></td>"
            else:
                cell_data = trade_matrix.get(m1, {}).get(m2, {'count': 0, 'details': []})
                trade_amt = cell_data['count']
                trade_details = "<hr style='border-color:#555;'>".join(cell_data['details'])
                bg_color = get_gradient_color(trade_amt, max_matrix_trades)
                
                if trade_amt > 0:
                    html_content += f"""
                        <td class='matrix-cell' style='background-color: {bg_color};'>
                            {trade_amt}
                            <div class='tooltiptext'>{trade_details}</div>
                        </td>
                    """
                else:
                    html_content += f"<td class='matrix-cell' style='background-color: {bg_color};'>{trade_amt}</td>"
                    
        html_content += "</tr>"

    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """

    with open("all_time_trade_counts.html", "w", encoding="utf-8") as file:
        file.write(html_content)

    print("Success! The results have been saved to 'all_time_trade_counts.html'.")

if __name__ == "__main__":
    main()