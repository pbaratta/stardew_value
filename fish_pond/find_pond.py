import json
from dataclasses import dataclass
import argparse

@dataclass
class StardewData:
	objects: dict
	fish_ponds: list

def load_stardew():
	with open('data/FishPondData.json', encoding='utf-8') as f:
		fish_ponds = json.load(f)

	with open('data/Objects.json', encoding='utf-8') as f:
		objects = json.load(f)

	return StardewData(
		objects=objects,
		fish_ponds=fish_ponds
	)

@dataclass
class ReportSettings:
	aged: bool = False
	artisan: bool = False

PARSER = argparse.ArgumentParser()

PARSER.add_argument(
	'--aged',
	action='store_true'
)

PARSER.add_argument(
	'--artisan',
	action='store_true'
)

def get_CLI_settings():
	args = PARSER.parse_args()
	settings = ReportSettings(
		aged=args.aged,
		artisan=args.artisan
	)
	if settings.artisan:
		settings.aged = True

	return settings


def main():
	data = load_stardew()
	settings = get_CLI_settings()

	report_fish_ponds(data, settings)


def normalize_fish_name(name):
	return (
		name
		.replace(' ', '')
		.replace('_', '')
		.lower()
	)

def pond_matches(fish, pond):
	' check if a fish is suitable for pond '
	tags = set(fish['ContextTags'])
	normal_name = normalize_fish_name(fish['Name'])

	for required in pond['RequiredTags']:
		if required.startswith('item_'):
			if normal_name != normalize_fish_name(required[5:]):
				return False

		elif required not in tags:
			return False

	return True

DEBUG = False

def find_pond(data, fish_id):
	' check all ponds for the best one for a given fish '
	fish = data.objects[fish_id]
	best_index = None
	best_pond = None
	best_precedence = float('inf')
	matches = []

	for index, pond in enumerate(data.fish_ponds):
		if not pond_matches(fish, pond):
			continue

		precedence = pond.get('Precedence', 1000)

		matches.append(
			(index, pond['Id'], precedence)
		)

		if precedence < best_precedence:
			best_precedence = precedence
			best_index = index
			best_pond = pond

	if DEBUG:
		print(f'{fish_id}\t{fish['Name']}\t{best_index}\t{matches}')

	return best_index, best_pond




def format_fish_produce(data, fish_id):
	'  '
	_, pond = find_pond(data, fish_id)
	if pond is None:
		return

	print(f'{fish_id}:')
	print(f'\tName: {OBJECTS[fish_id]['Name']}')
	print(f'\tBaseMinProduceChance: {pond['BaseMinProduceChance']}')
	print(f'\tBaseMaxProduceChance: {pond['BaseMaxProduceChance']}')

	max_population = pond['MaxPopulation']
	if max_population < 0:
		max_population = 10
	print(f'\tMaxPopulation: {max_population}')


	if pond['BaseMinProduceChance'] >= pond['BaseMaxProduceChance']:
		anything_produced_chance = pond['BaseMinProduceChance']
	else:
		anything_produced_chance = lerp(pond['BaseMinProduceChance'], pond['BaseMaxProduceChance'], max_population / 10.)

	print(f'\tanything_produced_chance: {anything_produced_chance}')

	fish = OBJECTS[fish_id]
	for item in pond['ProducedItems']:
		print(f'\tProducedItem: {item['ItemId']}')
		print(f'\t\tRequiredPopulation: {item['RequiredPopulation']}')
		print(f'\t\tChance: {item['Chance']}')
		#
		if item['Precedence'] != 0:
			print(f'\t!\tPrecedence: {item['Precedence']}')
		#
		if item['Condition']:
			print(f'\t!\tCondition: {item['Condition']}')
		#
		if item['MinStack'] != -1 or item['MaxStack'] != -1:
			print(f'\t!\tMinStack: {item['MinStack']}')
			print(f'\t!\tMaxStack: {item['MaxStack']}')



class NoPond(Exception):
	pass

def calculate_pond_outputs(data, fish_id):
	' iterable of (chance, item, average quantity) as they are enumerated '

	_, pond = find_pond(data, fish_id)
	if not pond:
		raise NoPond

	fish_id = '(O)' + fish_id  # for legend checks

	max_population = pond['MaxPopulation']
	if max_population < 0:
		max_population = 10

	if pond['BaseMinProduceChance'] >= pond['BaseMaxProduceChance']:
		anything_produced_chance = pond['BaseMinProduceChance']
	else:
		anything_produced_chance = lerp(pond['BaseMinProduceChance'], pond['BaseMaxProduceChance'], max_population / 10.)


	remaining_probability = 1.0
	def consume_probability(probability, item, quantity):
		nonlocal remaining_probability

		actual_probability = remaining_probability * probability
		remaining_probability -= actual_probability

		return actual_probability, item, quantity


	yield consume_probability(1 - anything_produced_chance, None, 0)

	for item in pond['ProducedItems']:

		# check population
		assert max_population >= item['RequiredPopulation']

		# check condition
		if item['Condition']:
			words = item['Condition'].split()
			if words[:2] != ['ITEM_ID', 'Input']:
				raise ValueError('Condition cannot be parsed due to hardcoaded logic')
			if fish_id not in words[2:]:
				continue

		min_stack = max(item['MinStack'], 1)
		max_stack = max(item['MaxStack'], min_stack)
		average_stack = (min_stack + max_stack) / 2

		item_id = item['ItemId']
		prefix, item_id = item_id[:3], item_id[3:]
		assert prefix == '(O)'

		yield consume_probability(item['Chance'], item_id, average_stack)

	if remaining_probability:
		yield (remaining_probability, None, 0)


def lerp(a, b, t):
	return a + t * (b - a)

import collections
ROE = '812'
BONUS_ROE = 0.25

def adjust_roe_quantity(item, quantity):
	if item == ROE:
		return quantity + 0.25

	return quantity


def tally_outputs(data, fish_id):

	outputs = collections.defaultdict(list)

	for chance, item, count in calculate_pond_outputs(data, fish_id):
		outputs[item].append((chance, count))

	nothing_chance =0
	for item, tallies in outputs.items():
		if len(tallies) == 1:
			chance, count = tallies[0]
		else:
			chance, count = weighted_average(tallies)

		count = adjust_roe_quantity(item, count)
		if item is None:
			nothing_chance = chance
			continue

		yield (item, count, chance)

	yield (None, 0, nothing_chance)


def calculate_sell_price(data, settings, item_id, source_fish_id):

	price = data.objects[item_id]['Price']

	if item_id != ROE:  # typical price, no roe adjustment
		return price

	fish_price = data.objects[source_fish_id]['Price']
	price += int(fish_price / 2)

	if not settings.aged:  # unaged roe, includes fish value
		return price  

	price *= 2

	if not settings.artisan:  # aged roe, not artisan
		return price

	price *= 1.4
	return int(price)  # aged roe, artisan


def weighted_average(tallies):
	total_chance =0
	total_weight =0

	for chance, count in tallies:
		total_chance += chance
		total_weight += chance * count

	return (total_chance, total_weight / total_chance)


def all_fish(data):
	for item_id, obj in data.objects.items():
		if obj.get('Type') == 'Fish':
			yield item_id

	# extra objects that count as fish (Coral and Sea Urchin)
	EXTRA_FISH = ('393', '397')
	yield from EXTRA_FISH


def report_fish_ponds(data, settings):
	total_value_by_fish = []
	for fish_id in all_fish(data):
		fish_name = data.objects[fish_id]['Name']
		print(f'{fish_name} ({fish_id})')
		try:
			expected_value =0
			for item_id, count, chance in tally_outputs(data, fish_id):
				if item_id is None:
					print(f'\tNothing: {chance:0.3f}')
					continue

				item_name = data.objects[item_id]['Name']
				item_price = calculate_sell_price(data, settings, item_id, fish_id)
				total_price = item_price * count
				expected_value += chance * total_price

				out = '\t' + item_name
				if count == 1:
					pass
				elif count == int(count):
					out += f'({int(count)})'
				else:
					out += f'({count:0.1f})'

				if total_price == int(total_price):
					out += f'[{int(total_price)}]: '
				else:
					out += f'[{total_price:0.0f}]: '

				out += f'{chance:0.3f}'
				print(out)

			total_value_by_fish.append((expected_value, fish_name))
			print(f'\tExpected Daily Value: {expected_value:0.3f}')
		except NoPond:
			pass

	total_value_by_fish.sort(reverse=True)

	print('')
	print('~' * 80)
	print('')

	for value, name in total_value_by_fish:
		print(f'{name}\t{value:0.3f}')


if __name__ == '__main__':
	main()




'''



(O)152	Seaweed
(O)153	Green Algae
(O)157	White Algae
(O)166	Treasure Chest
(O)168	Trash
(O)169	Driftwood
(O)170	Broken Glasses
(O)171	Broken CD
(O)172	Soggy Newspaper
(O)226	Spicy Eel
(O)305	Void Egg
(O)309	Acorn
(O)310	Maple Seed
(O)311	Pine Cone
(O)338	Refined Quartz
(O)378	Copper Ore
(O)380	Iron Ore
(O)384	Gold Ore
(O)386	Iridium Ore
(O)388	Wood
(O)390	Stone
(O)392	Nautilus Shell
(O)393	Coral
(O)394	Rainbow Shell
(O)397	Sea Urchin
(O)457	Pale Broth
(O)535	Geode
(O)536	Frozen Geode
(O)537	Magma Geode
(O)543	Dolomite
(O)571	Limestone
(O)66	Amethyst
(O)680	Green Slime Egg
(O)684	Bug Meat
(O)688	Warp Totem: Farm
(O)689	Warp Totem: Mountains
(O)690	Warp Totem: Beach
(O)709	Hardwood
(O)72	Diamond
(O)74	Prismatic Shard
(O)749	Omni Geode
(O)766	Slime
(O)768	Solar Essence
(O)769	Void Essence
(O)770	Mixed Seeds
(O)787	Battery Pack
(O)791	Golden Coconut
(O)797	Pearl
(O)80	Quartz
(O)802	Cactus Seeds
(O)812	Roe
(O)814	Squid Ink
(O)831	Taro Tuber
(O)84	Frozen Tear
(O)848	Cinder Shard
(O)851	Magma Cap
(O)852	Dragon Tooth
(O)857	Tiger Slime Egg
(O)91	Banana
(O)CaveJelly	Cave Jelly
(O)RiverJelly	River Jelly
(O)SeaJelly	Sea Jelly



'''