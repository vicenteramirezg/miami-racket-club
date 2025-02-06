def calculate_dominance_factor(set_scores):
    winner_games = 0
    loser_games = 0

    for set_score in set_scores:
        winner_games += set_score[0]
        loser_games += set_score[1]

    total_games = winner_games + loser_games
    if total_games == 0:
        return 0  # Avoid division by zero

    dominance_factor = (winner_games - loser_games) / total_games
    return dominance_factor

def adjust_k_factor(base_k, dominance_factor):
    # Scale the K-factor based on the dominance factor
    # You can adjust the scaling factor to control the impact of dominance
    return base_k * (1 + dominance_factor * 1.2)