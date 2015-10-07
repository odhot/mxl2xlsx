#!/usr/bin/env python

import pprint
# print = pprint.pprint

import sys
import math
from copy import copy

from utils import absolute2relative

import xlsxwriter
import xml.etree.ElementTree as ET
try:
    file_path = sys.argv[1] # file path as first command line argument
except IndexError:
    sys.exit("Error: input musicXML file as first argument.")


mxml = ET.parse(file_path)
score_partwise = mxml.getroot()
#assume P1 is always angklung, (TODO: add check)
part_angklung = score_partwise.find('part')

attributes = part_angklung.find('measure/attributes')
divisions = int(attributes.find('divisions').text)
# print(divisions)
#time_signature = attributes.find('./time') # TODO: save time signature data

note_queue = []
key_signature_list = []
beat_counter = 0
tie_start = False
num_of_staffs = 1

# import pdb;pdb.set_trace()

for measure in part_angklung:
    for child in measure:
        if child.tag == 'attributes':
            if child.find('key/fifths') is not None:
                key_signature_list.append({
                    'key_signature': int(child.find('key/fifths').text),
                    'position': beat_counter
                })

        elif child.tag == 'note':
            note = child # for easier code reading
            new_note = {}

            if note.find('pitch') is not None:
                new_note['type'] = 'pitch'
                new_note['step'] = note.find('pitch/step').text
                try:
                    new_note['alter'] = int(note.find('pitch/alter').text)
                except AttributeError:
                    new_note['alter'] = 0
                new_note['octave'] = int(note.find('pitch/octave').text)
            elif note.find('rest') is not None:
                new_note['type'] = 'rest'
            else:
                # import pdb;pdb.set_trace()
                sys.exit("Invalid MusicXML")

            new_note['duration'] = int(note.find('duration').text)
            if note.find('dot'):
                new_note['duration'] *= 1.5

            tie_tags = note.findall('tie')
            for tie_tag in tie_tags:
                if tie_tag.get('type') == 'stop':
                    old_duration = new_note['duration']
                    new_note = copy(tie_note)
                    new_note['duration'] = old_duration + tie_note['duration']
                    tie_start = False
                if tie_tag.get('type') == 'start':
                    tie_note = copy(new_note)
                    tie_start = True
            if tie_start:
                continue

            if note.find('chord') is not None:
                beat_counter -= new_note['duration']

            new_note['position'] = beat_counter

            if note.find('staff') is not None:
                staff = int(note.find('staff').text)
                new_note['staff'] = staff - 1
                if staff > num_of_staffs:
                    num_of_staffs = staff
            else:
                new_note['staff'] = 0

            note_queue.append(new_note)
            beat_counter += new_note['duration']

        elif child.tag == 'backup':
            beat_counter -= int(child.find('duration').text)

# print(note_queue, width=100, compact=True)
# print(key_signature_list, width=100, compact=True)
# print(beat_counter)
# sys.exit()

# print(num_of_staffs)
music_score_grid = [] # music_score > staff > line
for i in range(num_of_staffs):
    music_score_grid.append([[]])
    for j in range(beat_counter):
        music_score_grid[i][0].append(0)

while note_queue:
    note = note_queue.pop()
    if note['type'] == 'pitch':
        staff = note['staff']
        line = 0
        empty = True
        # print(staff, line, music_score_grid)
        for i, n in enumerate(music_score_grid[staff][line]):
            if n != 0 and i <= note['position'] and i + int(n[1:]) > note['position']:
                empty = False
        while not empty:
            line += 1
            try:
                music_score_grid[staff][line]
            except IndexError:
                music_score_grid[staff].append([])
                for i in range(beat_counter):
                    music_score_grid[staff][line].append(0)
            empty = True
            for i, n in enumerate(music_score_grid[staff][line]):
                if n != 0 and i <= note['position'] and i + int(n[1:]) > note['position']:
                    empty = False

        for i in range(len(key_signature_list) - 1, -1, -1):
            if note['position'] >= key_signature_list[i]['position']:
                keysig = key_signature_list[i]['key_signature']
                break
        else:
            raise Exception('key signature not found')

        music_score_grid[staff][line][note['position']] = absolute2relative(
            keysig, note['step'], note['alter'], note['octave']) + str(note['duration'])

# print(music_score_grid, width=95, compact=True)
pprint.pprint(music_score_grid, width=95, compact=True)
# sys.exit()

music_score_cells = []
line_counter = 0

for staff in music_score_grid:
    for line in music_score_grid:
        music_score_cells.append([])
        note_string_duration = 0
        for note in line:
            if note != 0:
                note_step = note[:1]
                note_duration = int(note[1:])
                note_val = note_duration/divisions
                if note_val == 0.25:
                    note_prefix = '-='
                elif note_val == 0.5:
                    note_prefix = '-'
                # elif note_val == 1/3:
                #     note_prefix = 't'
                elif note_val > divisions:
                    note_prefix = ''
                else:
                    if note_val == 0.75:
                        note_prefix = '?' #TODO
                    else:
                        raise Exception('unknown note value')
                note_string = note_prefix + note_step
                note_string_duration += note_duration
                # kumpulkan dulu jadi satu ketuk baru append
                music_score_cells[line_counter].append(note_string)
        line_counter += 1

pprint.pprint(music_score_cells, width=95, compact=True)
