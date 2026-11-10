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
            if roster_id:
                roster_map[roster_id] = user_map.get(owner_id, f"Team {roster_id}")
                
        return roster_map

def get_gradient_color(win_pct):
    hue = win_pct * 120
    return f"hsl({hue}, 75%, 35%)"

def calculate_win_pct(w, l, t):
    total = w + l + t
    if total == 0:
        return 0.0
    return (w + (t * 0.5)) / total

def main():
    if len(sys.argv) < 2:
        print("Error: Please provide a League ID.")
        sys.exit(1)
        
    current_league_id = sys.argv[1]
    client = SleeperClient()

    print(f"Fetching league data for ID: {current_league_id}")
    league_info = client.get_league_info(current_league_id)
    
    if not league_info:
        print("Could not load league info. Exiting.")
        return
        
    league_name = league_info.get('name', 'Unknown League')
    print(f"Processing: {league_name}")

    team_mapping = client.get_team_mapping(current_league_id)
    roster_ids = list(team_mapping.keys())

    all_play_records = {r_id: {'W': 0, 'L': 0, 'T': 0} for r_id in roster_ids}
    actual_records = {r_id: {'W': 0, 'L': 0, 'T': 0, 'details': []} for r_id in roster_ids}
    schedule_matrix = {r_id: {sched_id: {'W': 0, 'L': 0, 'T': 0, 'details': []} for sched_id in roster_ids} for r_id in roster_ids}

    played_weeks_data = []
    
    print("Gathering weekly scores and schedules...")
    for week in range(1, 19):
        matchups = client.get_matchups(current_league_id, week)
        if not matchups:
            break
            
        total_points = sum(m.get('points', 0) for m in matchups)
        if total_points == 0:
            break
            
        matchup_map = {}
        for m in matchups:
            mid = m['matchup_id']
            if mid not in matchup_map:
                matchup_map[mid] = []
            matchup_map[mid].append(m['roster_id'])
            
        week_data = {}
        for m in matchups:
            r_id = m['roster_id']
            pts = m.get('points', 0)
            
            mid = m['matchup_id']
            opponents = [r for r in matchup_map[mid] if r != r_id]
            opp_id = opponents[0] if opponents else None
            
            week_data[r_id] = {'points': pts, 'opponent_id': opp_id}
            
        played_weeks_data.append(week_data)

    print(f"Processed {len(played_weeks_data)} played weeks. Calculating records...")

    for week_idx, week_data in enumerate(played_weeks_data, 1):
        for r_id_A in roster_ids:
            if r_id_A not in week_data: continue
            team_a_pts = week_data[r_id_A]['points']

            actual_opp_id = week_data[r_id_A]['opponent_id']
            if actual_opp_id and actual_opp_id in week_data:
                actual_opp_pts = week_data[actual_opp_id]['points']
                opp_name = team_mapping.get(actual_opp_id, f"Team {actual_opp_id}")
                
                if team_a_pts > actual_opp_pts:
                    actual_records[r_id_A]['W'] += 1
                    res_str = "<span style='color: #00d287;'>W</span>"
                elif team_a_pts < actual_opp_pts:
                    actual_records[r_id_A]['L'] += 1
                    res_str = "<span style='color: #ff4a4a;'>L</span>"
                else:
                    actual_records[r_id_A]['T'] += 1
                    res_str = "<span style='color: #ffb800;'>T</span>"
                
                actual_records[r_id_A]['details'].append(
                    f"Wk {week_idx}: {team_a_pts:.2f} - {actual_opp_pts:.2f} vs {opp_name} ({res_str})"
                )

            for r_id_B in roster_ids:
                if r_id_A == r_id_B: continue
                if r_id_B not in week_data: continue
                
                team_b_pts = week_data[r_id_B]['points']
                if team_a_pts > team_b_pts:
                    all_play_records[r_id_A]['W'] += 1
                elif team_a_pts < team_b_pts:
                    all_play_records[r_id_A]['L'] += 1
                else:
                    all_play_records[r_id_A]['T'] += 1

            for r_id_B in roster_ids:
                if r_id_B not in week_data: continue
                
                opp_id = week_data[r_id_B]['opponent_id']
                if not opp_id: continue 
                if opp_id == r_id_A: continue 
                
                opp_pts = week_data[opp_id]['points']
                opp_name = team_mapping.get(opp_id, f"Team {opp_id}")
                
                if team_a_pts > opp_pts:
                    schedule_matrix[r_id_A][r_id_B]['W'] += 1
                    res_str = "<span style='color: #00d287;'>W</span>"
                elif team_a_pts < opp_pts:
                    schedule_matrix[r_id_A][r_id_B]['L'] += 1
                    res_str = "<span style='color: #ff4a4a;'>L</span>"
                else:
                    schedule_matrix[r_id_A][r_id_B]['T'] += 1
                    res_str = "<span style='color: #ffb800;'>T</span>"
                    
                schedule_matrix[r_id_A][r_id_B]['details'].append(
                    f"Wk {week_idx}: {team_a_pts:.2f} - {opp_pts:.2f} vs {opp_name} ({res_str})"
                )

    all_play_sorted = []
    for r_id, rec in all_play_records.items():
        all_play_pct = calculate_win_pct(rec['W'], rec['L'], rec['T'])
        act_rec = actual_records[r_id]
        act_pct = calculate_win_pct(act_rec['W'], act_rec['L'], act_rec['T'])
        
        all_play_sorted.append({
            'manager': team_mapping.get(r_id, "Unknown"),
            'w': rec['W'],
            'l': rec['L'],
            't': rec['T'],
            'pct': all_play_pct,
            'act_w': act_rec['W'],
            'act_l': act_rec['L'],
            'act_t': act_rec['T'],
            'act_pct': act_pct
        })
    all_play_sorted.sort(key=lambda x: x['pct'], reverse=True)

    sorted_managers = [team_mapping[r_id] for r_id in roster_ids]
    sorted_managers.sort(key=lambda x: x.lower())
    manager_to_rid = {v: k for k, v in team_mapping.items()}

    print("Generating HTML file...")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{league_name} - Advanced Records</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #121212; color: #e0e0e0; }}
            h2 {{ text-align: center; color: #ffffff; margin-top: 40px; }}
            table {{ width: 90%; margin: 20px auto; border-collapse: collapse; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5); background-color: #1e1e1e; }}
            th, td {{ padding: 12px; text-align: center; border: 1px solid #333; }}
            th {{ background-color: #2c2c2c; color: #ffffff; font-size: 14px; }}
            tr:hover {{ background-color: #2a2a2a; }}
            .score {{ font-weight: bold; color: #ffffff; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); }}
            .matrix-table th {{ background-color: #1c1c1c; position: sticky; top: 0; z-index: 2; }}
            .matrix-cell, .matrix-diagonal {{ position: relative; cursor: pointer; }}
            .matrix-cell {{ font-weight: bold; color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); }}
            .matrix-diagonal {{ background-color: #1a1a1a; font-weight: bold; color: #888; border: 2px solid #444; }}
            .subtitle {{ text-align: center; color: #aaa; margin-top: -15px; font-size: 14px; margin-bottom: 20px; }}
            .divider {{ border-left: 2px solid #555; }}
            
            .tooltiptext {{
                visibility: hidden;
                width: 280px;
                background-color: #2c2c2c;
                color: #e0e0e0;
                text-align: left;
                padding: 12px;
                border-radius: 6px;
                border: 1px solid #555;
                position: absolute;
                z-index: 10;
                bottom: 110%;
                left: 50%;
                margin-left: -140px;
                opacity: 0;
                transition: opacity 0.2s;
                font-weight: normal;
                text-shadow: none;
                font-size: 13px;
                max-height: 250px;
                overflow-y: auto;
                box-shadow: 0 4px 12px rgba(0,0,0,0.8);
                line-height: 1.5;
            }}
            .matrix-cell:hover .tooltiptext, .matrix-diagonal:hover .tooltiptext {{
                visibility: visible;
                opacity: 1;
            }}
        </style>
    </head>
    <body>
        <h2>All-Play Records vs Actual</h2>
        <div class="subtitle">Comparing true performance against schedule luck</div>
        <table style="width: 80%;">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Manager</th>
                    <th>Actual Record</th>
                    <th>Actual Win %</th>
                    <th class="divider">All-Play Record</th>
                    <th>All-Play Win %</th>
                </tr>
            </thead>
            <tbody>
    """

    for rank, team_data in enumerate(all_play_sorted, 1):
        act_record_str = f"{team_data['act_w']}-{team_data['act_l']}"
        if team_data['act_t'] > 0: act_record_str += f"-{team_data['act_t']}"
        
        ap_record_str = f"{team_data['w']}-{team_data['l']}"
        if team_data['t'] > 0: ap_record_str += f"-{team_data['t']}"
        
        ap_bg_color = get_gradient_color(team_data['pct'])
        
        html_content += f"""
                <tr>
                    <td>{rank}</td>
                    <td>{team_data['manager']}</td>
                    <td>{act_record_str}</td>
                    <td>{team_data['act_pct']:.3f}</td>
                    <td class="divider score" style="background-color: {ap_bg_color};">{ap_record_str}</td>
                    <td>{team_data['pct']:.3f}</td>
                </tr>
        """

    html_content += """
            </tbody>
        </table>

        <h2>Schedule Swap Matrix</h2>
        <div class="subtitle">Rows = Team | Columns = If they played this manager's schedule (Hover for scores)</div>
        <table class="matrix-table">
            <thead>
                <tr>
                    <th>Manager</th>
    """
    
    for m in sorted_managers:
        html_content += f"<th>{m}</th>"
    html_content += "</tr></thead><tbody>"

    for manager_a in sorted_managers:
        html_content += f"<tr><th>{manager_a}</th>"
        rid_a = manager_to_rid[manager_a]
        
        for manager_b in sorted_managers:
            if manager_a == manager_b:
                act_rec = actual_records[rid_a]
                act_str = f"{act_rec['W']}-{act_rec['L']}"
                if act_rec['T'] > 0: act_str += f"-{act_rec['T']}"
                
                details_html = "<br>".join(act_rec['details'])
                if not details_html: details_html = "No matchups played."
                
                html_content += f"""
                    <td class='matrix-diagonal'>
                        {act_str}
                        <div class='tooltiptext'><b>Actual Matchups:</b><hr style='border-color:#444; margin:5px 0;'>{details_html}</div>
                    </td>
                """
            else:
                rid_b = manager_to_rid[manager_b]
                rec = schedule_matrix[rid_a][rid_b]
                
                win_pct = calculate_win_pct(rec['W'], rec['L'], rec['T'])
                bg_color = get_gradient_color(win_pct)
                
                record_str = f"{rec['W']}-{rec['L']}"
                if rec['T'] > 0: record_str += f"-{rec['T']}"
                
                details_html = "<br>".join(rec['details'])
                if not details_html: details_html = "No matchups played."
                
                html_content += f"""
                    <td class='matrix-cell' style='background-color: {bg_color};'>
                        {record_str}
                        <div class='tooltiptext'><b>Simulated Matchups:</b><hr style='border-color:#444; margin:5px 0;'>{details_html}</div>
                    </td>
                """
                
        html_content += "</tr>"

    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """

    with open("advanced_records.html", "w", encoding="utf-8") as file:
        file.write(html_content)

    print("Success! The results have been saved to 'advanced_records.html'.")

if __name__ == "__main__":
    main()