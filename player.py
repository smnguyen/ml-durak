import durak

import math
import random
import util
import copy
import pickle


class Player(object):
    NO_VALID_MOVES = -1
    PASS_TURN = -2

    def __init__(self, verbose):
        self.hand = []
        self.name = random.randint(0, 1000000)
        self.verbose = verbose
        self.wins = 0

        # For card counting
        self.opponentHand = []
        self.maxCards = [max(durak.Card.RANKS) for _ in durak.Card.SUITS]
        self.unseenCards = set(durak.getDeck())

    def attack(self, table, trumpCard, deckSize, opponentHandSize, trashCards):
        """
        Given |table| a list of cards on the table, where table[0] is the
        top card, the player can choose a valid attacking card to play, or
        give up the attack. self.success must be set to True or False depending
        on the player's action. Returns the card the player chose,
        Player.NO_VALID_MOVES, or Player.PASS_TURN as appropriate.
        """
        if self.verbose >= 1:
            print "----ATTACK----"
            print "  %s's hand: " % self.name, self.hand
            print "  The table: ", table

        if len(table) == 0:
            i = self.beginAttack(trumpCard, deckSize, opponentHandSize, trashCards)
            attackCard = self.hand[i]
        else:
            attackingOptions = self.getAttackingCards(table)
            if len(attackingOptions) == 0:
                self.success = False
                if self.verbose >= 1:
                    print "  %s cannot attack." % self.name
                return Player.NO_VALID_MOVES

            i = self.chooseAttackCard(attackingOptions, table, trumpCard,
                                      deckSize, opponentHandSize, trashCards)
            if i == -1:
                self.success = False
                if self.verbose >= 1:
                    print "  %s gives up the attack." % self.name
                return Player.PASS_TURN
            attackCard = attackingOptions[i]

        table.insert(0, attackCard)
        self.hand.remove(attackCard)
        if attackCard.rank == self.maxCards[attackCard.suit]:
            self.maxCards[attackCard.suit] -= 1
        self.success = True
        if self.verbose >= 1:
            print "  %s attacks with %s" % (self.name, attackCard)
        return attackCard

    def beginAttack(self, trumpCard, deckSize, opponentHandSize, trashCards):
        """
        Returns an index from |self|.hand of the chosen card to begin attack.
        """
        raise NotImplementedError("Abstract function requires overriding")

    def chooseAttackCard(self, options, table, trumpCard, deckSize, opponentHandSize, trashCards):
        """
        Returns an index from |options| of the chosen card for attacking (-1 to stop attacking).
        """
        raise NotImplementedError("Abstract function requires overriding")

    def defend(self, table, trumpCard, deckSize, opponentHandSize, trashCards):
        """
        Given |table| a list of cards on the table, where table[0] is the top
        card, and |trumpSuit|, the player can choose a valid defending card
        to play, or surrender to the attacker. self.success must be set to
        True or False depending on the player's action. Returns the card the
        player chose, Player.NO_VALID_MOVES, or Player.PASS_TURN as appropriate.
        """
        if self.verbose >= 1:
            print "----DEFEND----"
            print "  %s's hand: " % self.name, self.hand
            print "  The table: ", table

        defendingOptions = self.getDefendingCards(table[0], trumpCard.suit)
        if len(defendingOptions) == 0:
            self.success = False
            if self.verbose >= 1:
                print "  %s cannot defend." % self.name
            return Player.NO_VALID_MOVES

        i = self.chooseDefenseCard(defendingOptions, table, trumpCard,
                                   deckSize, opponentHandSize, trashCards)
        if i == -1:
            self.success = False
            if self.verbose >= 1:
                print "  %s surrenders." % self.name
            return Player.PASS_TURN

        table.insert(0, defendingOptions[i])
        self.hand.remove(defendingOptions[i])
        if defendingOptions[i].rank == self.maxCards[defendingOptions[i].suit]:
            self.maxCards[defendingOptions[i].suit] -= 1
        self.success = True
        if self.verbose >= 1:
            print "  %s defends with %s" % (self.name, defendingOptions[i])
        return defendingOptions[i]

    def chooseDefenseCard(self, options, table, trumpCard, deckSize, opponentHandSize, trashCards):
        """
        Returns an index from |options| of the chosen card for defending (-1 to surrender).
        """
        raise NotImplementedError("Abstract function requires overriding")

    def refillHand(self, deck, sortHand=False):
        while len(self.hand) < 6 and len(deck) > 0:
            card = deck.pop()
            self.hand.append(card)
            self.unseenCards.discard(card)
        if sortHand:
            self.hand.sort(key=lambda c: (c.suit, c.rank))
    
    def getAttackingCards(self, table):
        """
        Valid attacking cards are those of the same rank as any
        of the cards on the table.
        """
        validRanks = set([card.rank for card in table])
        return filter(lambda c: c.rank in validRanks, self.hand)

    def getDefendingCards(self, aCard, trumpSuit):
        """
        Valid defending cards are those of the same suit as the attacking card,
        but of higher rank. If the attacking card is not a trump card, any trump
        cards are also valid attacking cards.
        """
        cards = filter(lambda c: c.suit == aCard.suit and c.rank > aCard.rank, self.hand)
        if aCard.suit != trumpSuit:
            cards.extend(filter(lambda c: c.suit == trumpSuit, self.hand))
        return cards

    def removeOpponentCard(self, card):
        if not isinstance(card, durak.Card): return

        try:
            self.opponentHand.remove(card)
        except ValueError:
            pass

        if card.rank == self.maxCards[card.suit]:
            self.maxCards[card.suit] -= 1
        self.unseenCards.discard(card)

    def addCards(self, table):
        self.hand.extend(table)

        for card in table:
            if card.rank > self.maxCards[card.suit]:
                self.maxCards[card.suit] = card.rank

    def addOpponentCards(self, table):
        self.opponentHand.extend(table)

        for card in table:
            if card.rank > self.maxCards[card.suit]:
                self.maxCards[card.suit] = card.rank

    def TDUpdateAttack(self, state, newState, reward):
        pass

    def TDUpdateDefend(self, state, newState, reward):
        pass

    def reset(self):
        """
        Resets the game state in preparation for a new game.
        """
        self.hand = []
        self.opponentHand = []


class HumanPlayer(Player):
    """
    Given a list of cards to play, the human player inputs the 0-based index
    of the card s/he wants to play.
    """
    def __init__(self, verbose):
        super(self.__class__, self).__init__(verbose)
        self.rename()

    def beginAttack(self, trumpCard, deckSize, opponentHandSize, trashCards):
        return util.readIntegerInRange(0, len(self.hand),
                                       "  Select a card to begin attack, %s: " % self.name)

    def chooseAttackCard(self, options, table, trumpCard, deckSize, opponentHandSize, trashCards):
        print "  Attacking options: ", options
        return util.readIntegerInRange(-1, len(options),
                                       "  Select a card, %s (-1 to stop attack): " % self.name)

    def chooseDefenseCard(self, options, table, trumpCard, deckSize, opponentHandSize, trashCards):
        print "  Defending options: ", options
        return util.readIntegerInRange(-1, len(options),
                                       "  Select a card, %s (-1 to surrender): " % self.name)

    def rename(self):
        if self.verbose >= 1:
            print "Player %s, what would you like to call yourself?" % self.name

        name = raw_input()
        if name != '':
            self.name = name


class RandomCPUPlayer(Player):
    def __init__(self, verbose):
        super(self.__class__, self).__init__(verbose)

    def beginAttack(self, trumpCard, deckSize, opponentHandSize, trashCards):
        return random.randint(0, len(self.hand) - 1)

    def chooseAttackCard(self, options, table, trumpCard, deckSize, opponentHandSize, trashCards):
        return random.randint(-1, len(options) - 1)

    def chooseDefenseCard(self, options, table, trumpCard, deckSize, opponentHandSize, trashCards):
        return random.randint(-1, len(options) - 1)


class SimpleCPUPlayer(Player):
    """
    SimpleCPUPlayer always follows the policy of choosing the lowest-ranked non-trump
    card first. When there are no non-trump cards, SimpleCPUPlayer then chooses the
    lowest-ranked trump card available.
    """
    def __init__(self, verbose):
        super(self.__class__, self).__init__(verbose)

    def policy(self, options, trumpSuit):
        sortedOptions = sorted(options, key=lambda c: c.rank)
        nonTrumpCards = filter(lambda c: c.suit != trumpSuit, sortedOptions)
        trumpCards = filter(lambda c: c.suit == trumpSuit, sortedOptions)
        if len(nonTrumpCards) > 0:
            return options.index(nonTrumpCards[0])
        elif len(trumpCards) > 0:
            return options.index(trumpCards[0])

    def beginAttack(self, trumpCard, deckSize, opponentHandSize, trashCards):
        return self.policy(self.hand, trumpCard.suit)

    def chooseAttackCard(self, options, table, trumpCard, deckSize, opponentHandSize, trashCards):
        return self.policy(options, trumpCard.suit)

    def chooseDefenseCard(self, options, table, trumpCard, deckSize, opponentHandSize, trashCards):
        return self.policy(options, trumpCard.suit)


FULL_DECK = durak.getDeck(shuffle=False)


def avgRank(cards):
    rankSum = sum(c.rank for c in cards)
    if len(cards) == 0:
        return 0
    else:
        return float(rankSum) / len(cards)


def extractFeatures(hand, opponentHand, opponentHandSize,
                    trumpCard, table, deckSize, unseenCards):
    features = [len(hand), len(table), deckSize, opponentHandSize]
    for rank in durak.Card.RANKS:
        rankCards = filter(lambda c: c.rank == rank, hand)
        features.append(len(rankCards))
    royals = filter(lambda c: c.rank > 10, hand)

    clubs = filter(lambda c: c.suit == 0, hand)
    hearts = filter(lambda c: c.suit == 1, hand)
    diamonds = filter(lambda c: c.suit == 2, hand)
    spades = filter(lambda c: c.suit == 3, hand)
    trumps = filter(lambda c: c.suit == trumpCard.suit, hand)

    tableRanks = set([c.rank for c in table])
    attackCards = filter(lambda c: c.rank in tableRanks, hand)
    if len(tableRanks) > 0:
        defendCards = filter(lambda c: c.rank > max(tableRanks) or c.suit == trumpCard.suit, hand)
    else:
        defendCards = hand

    # cards we know the opponent has
    oppAttackCards = filter(lambda c: c.rank in tableRanks, opponentHand)
    expAttackCards = len(oppAttackCards)
    if len(tableRanks) > 0:
        oppDefendCards = filter(lambda c: c.rank > max(tableRanks) or c.suit == trumpCard.suit, opponentHand)
    else:
        oppDefendCards = opponentHand
    expDefendCards = len(oppDefendCards)

    # model expectation using hypergeometric distribution
    # if len(unseenCards) > 0:
    #     nUnknownCards = opponentHandSize - len(opponentHand)
    #     nAttackCards = len(filter(lambda c: c.rank in tableRanks, unseenCards))
    #     expAttackCards += nUnknownCards * nAttackCards / float(len(unseenCards))
    #     if len(tableRanks) > 0:
    #         nDefendCards = len(filter(lambda c: c.rank > min(tableRanks) or
    #                                             c.suit == trumpCard.suit, unseenCards))
    #         expDefendCards += nUnknownCards * nDefendCards / float(len(unseenCards))

    return features + [len(royals), len(clubs), len(hearts), len(diamonds), len(spades), len(trumps),
                       avgRank(clubs), avgRank(hearts), avgRank(diamonds), avgRank(spades), avgRank(trumps),
                       len(attackCards), len(defendCards), len(tableRanks), expAttackCards, expDefendCards]


def logisticValue(weights, features):
    z = sum(weight * feature for weight, feature in zip(weights, features))
    return 1.0 / (1 + math.exp(-z))


class ReflexCPUPlayer(Player):
    attackWeights = [random.gauss(0, 1e-2) for _ in range(29)]
    defendWeights = [random.gauss(0, 1e-2) for _ in range(29)]

    def __init__(self, verbose):
        super(self.__class__, self).__init__(verbose)

    def chooseAction(self, opts, table, trumpCard, deckSize, opponentHandSize, weights):
        maxV = None
        maxI = None
        for i, card in enumerate(opts):
            newHand = copy.deepcopy(self.hand)
            newHand.remove(card)
            features = extractFeatures(newHand, self.opponentHand, opponentHandSize,
                                       trumpCard, table + [card], deckSize, self.unseenCards)
            v = logisticValue(weights, features)
            if maxV is None or v > maxV:
                maxV = v
                maxI = i
        return maxI, maxV

    def beginAttack(self, trumpCard, deckSize, opponentHandSize, trashCards):
        maxI, maxV = self.chooseAction(self.hand, [], trumpCard, deckSize,
                                       opponentHandSize, self.attackWeights)
        return maxI

    def chooseAttackCard(self, options, table, trumpCard, deckSize, opponentHandSize, trashCards):
        maxI, maxV = self.chooseAction(options, table, trumpCard, deckSize,
                                       opponentHandSize, self.attackWeights)

        newDeckSize = deckSize - max(0, 6 - len(self.hand)) - max(0, 6 - opponentHandSize)
        stopFeatures = extractFeatures(self.hand, self.opponentHand, max(opponentHandSize, 6),
                                       trumpCard, [], newDeckSize, self.unseenCards)
        stopV = logisticValue(self.attackWeights, stopFeatures)
        if stopV > maxV:
            return -1
        else:
            return maxI

    def chooseDefenseCard(self, options, table, trumpCard, deckSize, opponentHandSize, trashCards):
        maxI, maxV = self.chooseAction(options, table, trumpCard, deckSize,
                                       opponentHandSize, self.defendWeights)

        newDeckSize = deckSize - max(0, 6 - len(self.hand + table)) - max(0, 6 - opponentHandSize)
        stopFeatures = extractFeatures(self.hand + table, self.opponentHand, max(opponentHandSize, 6),
                                       trumpCard, [], newDeckSize, self.unseenCards)
        stopV = logisticValue(self.defendWeights, stopFeatures)
        if stopV > maxV:
            return -1
        else:
            return maxI

    def TDUpdateAttack(self, state, newState, reward):
        stateFeatures = extractFeatures(*state)
        value = logisticValue(self.attackWeights, stateFeatures)
        residual = reward - value
        if newState is not None:
            newStateFeatures = extractFeatures(*newState)
            residual += logisticValue(self.attackWeights, newStateFeatures)
        gradient = [value * (1 - value) * feature for feature in stateFeatures]
        newWeights = [w + 1e-1 * residual * gradient_i
                      for w, gradient_i in zip(self.attackWeights, gradient)]
        self.attackWeights = newWeights

    def TDUpdateDefend(self, state, newState, reward):
        if state is None: return

        stateFeatures = extractFeatures(*state)
        value = logisticValue(self.defendWeights, stateFeatures)
        residual = reward - value
        if newState is not None:
            newStateFeatures = extractFeatures(*newState)
            residual += logisticValue(self.defendWeights, newStateFeatures)
        gradient = [value * (1 - value) * feature for feature in stateFeatures]
        newWeights = [w + 1e-1 * residual * gradient_i
                      for w, gradient_i in zip(self.defendWeights, gradient)]
        self.defendWeights = newWeights

    @staticmethod
    def writeWeights():
        with open('reflex_attack', 'w') as f:
            pickle.dump(ReflexCPUPlayer.attackWeights, f)
        with open('reflex_defend', 'w') as f:
            pickle.dump(ReflexCPUPlayer.defendWeights, f)

    @staticmethod
    def loadWeights():
        try:
            with open('reflex_attack', 'r') as f:
                ReflexCPUPlayer.attackWeights = pickle.load(f)
        except IOError:
            ReflexCPUPlayer.attackWeights = [random.gauss(0, 1e-2) for _ in range(29)]
        try:
            with open('reflex_defend', 'r') as f:
                ReflexCPUPlayer.defendWeights = pickle.load(f)
        except IOError:
            ReflexCPUPlayer.defendWeights = [random.gauss(0, 1e-2) for _ in range(29)]