import numpy as np
from template import Agent
from Splendor.splendor_model import SplendorGameRule
from math import log, sqrt
import time
import random
from copy import deepcopy
from collections import Counter
import heapq

# Constants
TIME_LIMIT = 0.9
NUMBER_PLAYERS = 2
EXPLORATION_PARAMETER = 0.8
END_GAME_THRESHOLD = 15
DISCOUNT_FACTOR = 0.9
SIMULATION_DEPTH = 40
gem = {'red': 0, 'green': 0, 'blue': 0, 'black': 0, 'white': 0, 'yellow': 0}
card = {'score': 0, 'red': 0, 'green': 0, 'blue': 0, 'black': 0, 'white': 0, 'yellow': 0}

# Initialize game rule
game_rule = SplendorGameRule(NUMBER_PLAYERS)

# Monte Carlo Tree Search node class
class MCTSNode:
    def __init__ (self, agent_id, game_state, parent, action):
        self.agent_id = agent_id
        self.game_state = deepcopy(game_state)
        self.parent = parent
        self.action = action
        self.children = []
        self.visits = 0
        self.value = 0
        self.untried_actions = game_rule.getLegalActions(game_state, agent_id)
        
    def SelectChild(self):
        # Use UCB1 formula to select the best child
        return max(self.children, key = lambda c: c.value/c.visits + EXPLORATION_PARAMETER * sqrt(2*log(self.visits)/c.visits))
    
# Priority Queue class
class PriorityQueue:
    def __init__(self):
        self.queue_index = 0
        self.priority_queue = []

    def push(self, item, priority):
        # Push an item into the queue with a priority
        heapq.heappush(self.priority_queue,(priority, self.queue_index, item))
        self.queue_index += 1

    def empty(self):
        # Check if the queue is empty
        return len(self.priority_queue) == 0

    def pop(self):
        # Pop the item with the highest priority
        return heapq.heappop(self.priority_queue)[-1]
            
# Monte Carlo Tree Search class
class MCTS:
    def __init__(self, agent_id, game_state):
        self.agent_id = agent_id
        self.game_state = game_state
    
    def HeuristicSelection(self, actions, state):
        # Use a heuristic function to prone the search space
        priority_queue = PriorityQueue()
        board_state = self.check_board(state,self.agent_id)
        start_time = time.time()

        for action in actions:
            if time.time() - start_time > TIME_LIMIT:
                break
            
            action_rewards = self.check_action(action)
            priority_queue.push(action, self.heuristic_func(board_state, action_rewards))
            
        # Return the action with the highest priority
        return priority_queue.pop() if not priority_queue.empty() else random.choice(actions)
    
    def heuristic_func(self, on_board, action_rewards):
        # Calculate the heuristic value of an action
        f1 = self.feature1(on_board, action_rewards)
        f2 = self.feature2(action_rewards)
        f3 = self.feature3(on_board)
        f4 = self.improved_feature4(on_board, action_rewards)
        f5 = self.feature5(on_board, action_rewards)
        current_score = on_board["score"]
        
        return self.phase_function(f1, f2, f3, f4, f5, current_score)

    def phase_function(self, f1, f2, f3, f4, f5, current_score):
        final_distance = f1
        gem_ecoaffect = f2
        card_diversity = f3
        gem_diversity = f4
        nobel_distance = f5
        
        # Late phase
        if current_score > 12:
            return 30 * final_distance + 2 * gem_ecoaffect + 10 * card_diversity + 10 * gem_diversity +  35 * nobel_distance 
        
        # Mid phase
        elif 6 < current_score <= 12:
            return 20 * final_distance + 2 * gem_ecoaffect + 10 * card_diversity + 15 * gem_diversity + 25 * nobel_distance
        
        # Early phase
        else:
            return 20 * final_distance + 2 * gem_ecoaffect + 10 * card_diversity + 10 * gem_diversity + 30 * nobel_distance       

    def feature1(self, on_board, action_rewards):
        # This feature measures the distance between the player and the winning score 
        # after performing a certain action.
        current_score = on_board["score"] + action_rewards["score_reward"]
        max_score = 15
        score_ratio = current_score / max_score # Simplify the calculation
        urgency = 1 - score_ratio
        
        return urgency
    
    def feature2(self, action_rewards):
        gem_cost = action_rewards["gem_rewards"].values()
        gem_change = sum(value if value > 0 else 8 * value for value in gem_cost)

        cardnum = sum(list(action_rewards["gem_cards_rewards"].values())[1:])
        card_income = action_rewards["gem_cards_rewards"]["score"]

        # Avoid division by zero errors and simplify the code
        denominator_income = max(1, card_income + 1)
        denominator_cards = max(1, cardnum + 1)

        # Use a constant to standardize the scores
        normalization_constant = 20
        f2score = -((gem_change / denominator_income) + (gem_change / denominator_cards)) / normalization_constant

        return f2score

    def feature3(self, on_board):
        gem_cards = on_board["my_gemcard"]
        diversity_score = 0
        # Calculate the diversity score of the card, and the processing here is the same as that of gems
        for card in gem_cards:
            if gem_cards[card] > 2:
                diversity_score -= (gem_cards[card] - 2) 
            else:
                diversity_score += 1 

        return diversity_score
        
    def feature4(self, on_board):
        gem_values = on_board["my_gem"]
        diversity_score = 0

        # Calculate the diversity score of gems
        for gem in gem_values:
            if gem_values[gem] > 4:
                # If there are more than 4 gems, each additional one will reduce a certain score
                diversity_score -= (gem_values[gem] - 4)
            else:
                # If less than or equal to 4, each one will increase a certain score
                diversity_score += 1
                
        return diversity_score
    
    def improved_feature4(self, on_board, action_rewards):
        # Calculate the diversity score of gems
        gem_values = list(on_board["my_gem"].values())[:-1]
        # Predict future gem card counts, excluding the last type of card reward
        gem_card_value = np.array(list(on_board["my_gemcard"].values()))
        card_re = np.array(list(action_rewards["gem_cards_rewards"].values())[1:])
        future_cardgems = gem_card_value + card_re
        # Calculate scores for each gem type when less than 4 gems are present
        scores = [4 - gem for gem in gem_values]
        total_score = sum(scores)  # Calculate total score
        normalized_score = total_score / (sum(future_cardgems[:-1]) + 1)
        last_gem_card_bonus = future_cardgems[-1] * 2
        # Final diversity score
        diversity_score = normalized_score + last_gem_card_bonus
        return diversity_score 

    def feature5(self, on_board, action_rewards):
        # Evaluate the contribution of a given action to attracting noble cards
        f5score = 0
        gem_cards = Counter(on_board["my_gemcard"])
        re = Counter({k: action_rewards['gem_cards_rewards'][k] for k in list(action_rewards['gem_cards_rewards'].keys())[1:]})
        this_gem_card = dict(re + gem_cards)
        nobles = on_board["noble"]
        for noble in nobles:
            f5score += abs(sum(dict(Counter(noble) - Counter(this_gem_card)).values()))
        f5score = f5score / 9
        
        return f5score
    
    def check_board(self, state, agent_id):
        board = {"score": state.agents[agent_id].score, "my_gem": {}, "my_gemcard": {}, "noble": []}
        
        # Initialize gem and card counts
        my_gem = {color: 0 for color in gem}
        my_gemcard = {color: 0 for color in gem}

        # Aggregate gems and cards held by the agent
        agent_gems = state.agents[agent_id].gems
        agent_cards = state.agents[agent_id].cards

        for color in gem:
            gem_count = agent_gems.get(color, 0)
            card_count = len(agent_cards.get(color, []))
            my_gem[color] = gem_count + card_count
            my_gemcard[color] = card_count

        board["my_gem"] = my_gem
        board["my_gemcard"] = my_gemcard

        # Process noble cards available on the board
        for noble in state.board.nobles:
            noble_requirements = noble[1]
            noble_card = {color: noble_requirements.get(color, 0) for color in gem}
            noble_card['score'] = 3
            board["noble"].append(noble_card)

        return board
    
    def check_action(self, action):
        # Check the rewards of a given action
        rewards = {
            "score_reward": 0,
            "gem_rewards": deepcopy(gem),
            "gem_cards_rewards": deepcopy(card)
        }

        action_type = action["type"]
        if action_type == "reserve":
            # Reserve a card
            rewards["gem_rewards"]["yellow"] = 1
            
        elif action_type in ['buy_available', 'buy_reserve']:
            # Buy a card
            rewards["score_reward"] += action['card'].points
            rewards["gem_cards_rewards"]["score"] = action['card'].points
            rewards["gem_cards_rewards"][action['card'].colour] = 1

            for color in rewards["gem_rewards"]:
                rewards["gem_rewards"][color] = -action['returned_gems'].get(color, 0)
                
        elif action_type in ["collect_same", "collect_diff"]:
            # Collect gems
            for color in rewards["gem_rewards"]:
                # Calculate the gem rewards
                collected = action['collected_gems'].get(color, 0)
                returned = action['returned_gems'].get(color, 0)
                rewards["gem_rewards"][color] = collected - returned
        
        # Check if the action leads to a noble card
        if action.get('noble'):
            rewards["score_reward"] += 3

        return rewards

    def Expand(self, node):
        # If there are untried actions, create a new child node
        if node.untried_actions:
            # Use Heuristic Selection to prioritize actions
            action = self.HeuristicSelection(node.untried_actions, node.game_state)
            new_game_state = game_rule.generateSuccessor(deepcopy(node.game_state), action, node.agent_id)
            new_node = MCTSNode(node.agent_id, new_game_state, node, action)
            node.children.append(new_node)
            # Remove the selected action from the untried actions
            node.untried_actions.remove(action)
            return new_node
        
        # The tree node is fully expanded
        return None
        
    def SelectAction(self):
        root = MCTSNode(self.agent_id, self.game_state, None, None)
        
        # Run MCTS for a fixed amount of time to avoid timeout
        start_time = time.time()
        while time.time() - start_time < TIME_LIMIT:
            node = root
            game_state = deepcopy(self.game_state)
            
            # Selection and expansion phase
            while not game_rule.gameEnds():
                # If the node is fully expanded, use UCB1 to select the best child
                if not node.untried_actions and node.children:
                    node = node.SelectChild()
                    game_state = game_rule.generateSuccessor(game_state, node.action, node.agent_id)
                else:
                    break
            if node.untried_actions:
                # Expand the node if it has untried actions
                node = self.Expand(node)
                game_state = game_rule.generateSuccessor(game_state, node.action, node.agent_id)
            
            # Simulation phase
            reward = self.Simulate(game_state, start_time)
            
            # Backpropagation phase
            self.Backpropagate(node, reward)
        
        # Select the best action based on the number of visits
        best_action = max(root.children, key = lambda c: c.visits).action
        
        return best_action
    
    def Simulate(self, game_state, start_time):
        reward = 0
        game_state = deepcopy(game_state)
        agent_id = self.agent_id
        simulation_depth = 1
        
        while not game_rule.gameEnds() and simulation_depth < SIMULATION_DEPTH:
            # Break if reaching the time limit
            if time.time() - start_time > TIME_LIMIT:
                break
            
            # Select the action using Heuristic Selection
            action = self.HeuristicSelection(game_rule.getLegalActions(game_state, self.agent_id), game_state)
            
            # Accumulate the reward
            if agent_id == self.agent_id:
                # Add the reward if it is the agent's turn
                reward += self.GetReward(action, game_state, self.agent_id) * (DISCOUNT_FACTOR ** simulation_depth)
            else:
                # Subtract the reward if it is the opponent's turn
                reward -= self.GetReward(action, game_state, self.agent_id) * (DISCOUNT_FACTOR ** simulation_depth)
                
            # Update the game state
            next_agent_id = 1 - agent_id
            game_state = game_rule.generateSuccessor(game_state, action, next_agent_id)

            simulation_depth += 1
        
        return reward

    def Backpropagate(self, node, value):
        # Backpropagate the reward to the root node
        while node:
            node.visits += 1
            node.value += value
            node = node.parent
            value = -value
            
    def GetReward(self, action, game_state, agent_id):
        reward = 0
        opponent_id = 1 - agent_id
        game_state = deepcopy(game_state)
        useful_cards = self.CheckUsefulCard(game_state)

        if action['type'] == 'buy_available' or action['type'] == 'buy_reserve':
            card = action['card']
            
            # Check if the card is useful
            if card in useful_cards:
                reward += 3
            
            # Check if buying the card will help achieve a noble
            noble_probabilities = self.CheckNobleProbability(game_state, agent_id)
            game_state_after_buy = game_rule.generateSuccessor(game_state, action, agent_id)
            noble_probabilities_after_buy = self.CheckNobleProbability(game_state_after_buy, agent_id)
            for noble in range(min(len(noble_probabilities), len(noble_probabilities_after_buy))):
                if noble_probabilities_after_buy[noble] > noble_probabilities[noble]:
                    reward += 3
                    
            # Check if opponent has high probability to buy the card
            opponent_card_probability = self.CheckCardProbability(game_state, opponent_id, card, game_state.agents[opponent_id].gems.get('yellow', 0))
            if opponent_card_probability > 0.75:
                reward += 1.5
                
            # Check if the card is useful for buying other useful cards
            for useful_card in useful_cards:
                if useful_card.points > card.points:
                    card_probability = self.CheckCardProbability(game_state, agent_id, useful_card, game_state.agents[agent_id].gems.get('yellow', 0))
                    if card_probability > 0.5:
                        reward += 3

        elif action['type'] == 'reserve':
            card = action['card']
            
            # Check if the card is useful
            if card in useful_cards:
                reward += 3
                
            # Check if after reserving the card, the player can buy useful cards in the next turn
            yellow_gems = game_state.agents[agent_id].gems.get('yellow', 0) + 1
            game_state_after_reserve = game_rule.generateSuccessor(game_state, action, agent_id)
            useful_cards_after_reserve = self.CheckUsefulCard(game_state_after_reserve)
            for useful_card in useful_cards_after_reserve:
                card_probability = self.CheckCardProbability(game_state_after_reserve, agent_id, useful_card, yellow_gems)
                if card_probability > 0.5:
                    reward += 3
                    
            # Check if the opponent has high probability to buy the reserved card
            opponent_card_probability = self.CheckCardProbability(game_state, opponent_id, card, game_state.agents[opponent_id].gems.get('yellow', 0))
            if opponent_card_probability > 0.75:
                reward += 1
                if card.points >= 3:
                    reward += 2
                
            # Penalize if the player reserves a card with very low probability to buy
            card_probability = self.CheckCardProbability(game_state, agent_id, card, yellow_gems)
            if card_probability < 0.25:
                reward -= 3
                
            # Penalize for returning gems
            reward -= 1 * sum(action['returned_gems'].values())
                             
        elif action['type'] == 'collect_diff' or action['type'] == 'collect_same':
            yellow_gems = game_state.agents[agent_id].gems.get('yellow', 0)
            game_state_after_collect = game_rule.generateSuccessor(game_state, action, agent_id)
            
            # Check if the probability of buying useful cards increases after collecting gems
            cards_prob_before = []
            for useful_card in useful_cards:
                card_probability = self.CheckCardProbability(game_state, agent_id, useful_card, yellow_gems)
                cards_prob_before.append(card_probability)
                
            cards_prob_after = []
            for useful_card in useful_cards:
                card_probability = self.CheckCardProbability(game_state_after_collect, agent_id, useful_card, yellow_gems)
                cards_prob_after.append(card_probability)
                
            for i in range(len(cards_prob_before)):
                if cards_prob_after[i] > cards_prob_before[i]:
                    reward += 3
                    
            # Check if the probability of buying reserved cards increases after collecting gems
            reserved_cards = game_state.agents[agent_id].cards['yellow']
            cards_prob_before = []
            for reserved_card in reserved_cards:
                card_probability = self.CheckCardProbability(game_state, agent_id, reserved_card, yellow_gems)
                cards_prob_before.append(card_probability)
                
            cards_prob_after = []
            for reserved_card in reserved_cards:
                card_probability = self.CheckCardProbability(game_state_after_collect, agent_id, reserved_card, yellow_gems)
                cards_prob_after.append(card_probability)
                
            for i in range(len(cards_prob_before)):
                if cards_prob_after[i] > cards_prob_before[i]:
                    reward += 1.5
                
            # Penalize for returning gems
            reward -= 1 * sum(action['returned_gems'].values())
                
            # Big penalty for returning yellow gems
            if 'yellow' in action['returned_gems']:
                reward -= 10
            
        if action.get('noble') is not None:
            reward += 5
        
        return reward
    
    def CheckNobleProbability(self, game_state, agent_id):
        # Check the probability of achieving each noble
        noble_probabilities = []
       
        for noble in game_state.board.nobles:
            noble_requirements = noble[1]
            cards_prob = []
            for card, count in noble_requirements.items():
                cards_prob.append(len(game_state.agents[agent_id].cards.get(card, [])) / count)
                 
            card_prob = min(cards_prob)
            noble_probabilities.append(card_prob)
            
        return noble_probabilities
    
    def CheckCardProbability(self, game_state, agent_id, card, yellow_gems):
        # Check the probability of achieving a specific card
        card_probabilities = []
        card_requirements = card.cost
        
        for color, count in card_requirements.items():
            gem_on_card = len(game_state.agents[agent_id].cards.get(color, []))
            gem = game_state.agents[agent_id].gems.get(color, 0)
            if gem_on_card >= count or gem >= count or (gem_on_card + gem) >= count:
                card_probabilities.append(1)
            elif (gem_on_card + yellow_gems) >= count:
                card_probabilities.append(1)
                yellow_gems -= count - gem_on_card
            elif (gem + yellow_gems) >= count:
                card_probabilities.append(1)
                yellow_gems -= count - gem
            elif (gem_on_card + gem + yellow_gems) >= count:
                card_probabilities.append(1)
                yellow_gems -= count - gem_on_card - gem
            else:
                card_probabilities.append((gem_on_card + gem + yellow_gems) / count)
                yellow_gems = 0
               
        return min(card_probabilities)
    
    def CheckUsefulCard(self, game_state):
        # Check if there are useful cards available on the board
        useful_cards = []
        dealt_list = game_state.board.dealt_list()
        
        for card in dealt_list:
            if card.points == 5:
                useful_cards.append(card)
            elif card.points == 4:
                if len(card.cost) == 1:
                    useful_cards.append(card)
            elif card.points == 3:
                if len(card.cost) == 1:
                    useful_cards.append(card)
            elif card.points == 2:
                if len(card.cost) == 1 or len(card.cost) == 2:
                    useful_cards.append(card)
            elif card.points == 1:
                total = 0
                for color in card.cost:
                    total += card.cost[color]
                if len(card.cost) == 1 or total == 7:
                    useful_cards.append(card)
                    
        return useful_cards
        
# Agent class
class myAgent(Agent):
    def __init__(self,_id):
        super().__init__(_id)
        
    def SelectAction(self, actions, game_state):    
        # Initialize MCTS
        mcts = MCTS(self.id, game_state)
        
        # Select the best action using MCTS
        best_action = mcts.SelectAction()
        
        return best_action