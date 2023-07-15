def assign_team_nj(row, roster, threshold=0.8):
    """Assign team for new jersey roster

    Parameters
    ----------
    row : match row
    roster : dict
        {puuid1:team, puuid2:team, ...} for all nj
    threshold : float, optional
        percent of players needed to match a team roster to a nj team, by default 0.8
    """
    if row['red_roster'] == []:
        return None, None
    # Extract puuids for red roster
    red_puuids = [item.get('puuid') for item in row['red_roster']]
    # Extract puuids for blue roster
    blue_puuids = [item.get('puuid') for item in row['blue_roster']]
    # Create list of red roster matches with overall roster
    red_team_matches = [roster.get(puuid, None) for puuid in red_puuids if roster.get(puuid, None) is not None]
    # Create list of blue roster matches with overall roster
    blue_team_matches = [roster.get(puuid, None) for puuid in blue_puuids if roster.get(puuid, None) is not None]
    # Check for teams
    red_team_homogeneity = sum([True if x==red_team_matches[0] else False for x in red_team_matches])
    if len(red_team_matches) / len(red_puuids) >= threshold and red_team_homogeneity == len(red_team_matches):
        red_team = red_team_matches[0]
    else:
        red_team = None
    blue_team_homogeneity = sum([True if x==blue_team_matches[0] else False for x in blue_team_matches])
    if len(blue_team_matches) / len(blue_puuids) >= threshold and blue_team_homogeneity == len(blue_team_matches):
        blue_team = red_team_matches[0]
    else:
        blue_team = None
    # If only one team detected, then still not a match
    if red_team is None or blue_team is None:
        red_team = None
        blue_team = None
    return red_team, blue_team