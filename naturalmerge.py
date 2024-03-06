import os
import itertools
import math
from random import randint

BUFFER_SIZE = 32
SET_BYTES_SIZE = 15
RECORD_BYTES_SIZE = SET_BYTES_SIZE + 1
BYTES_BUFFER_SIZE = BUFFER_SIZE * RECORD_BYTES_SIZE


class ReadBuffer:
    def __init__(self, file_path):
        self.read_pos = 0
        self.size = BUFFER_SIZE
        self.loaded_size = 0
        self.buffer = []
        self.file_path = file_path
        self.file_pos = 0
        self.file_size = os.path.getsize(file_path)
        self.disk_reads_count = 0
        self.load_next()

    # None if there is no next record
    def read_next(self):
        if not self.has_more():
            return None

        res_record = self.buffer[self.read_pos]
        self.read_pos += 1
        if self.read_pos == self.size:
            self.load_next()
            self.read_pos = 0

        return res_record


    def has_more(self):
        return (self.file_pos < self.file_size
                or self.read_pos < self.loaded_size)

    def peek(self):
        if self.read_pos == self.loaded_size:
            return None
        result = self.buffer[self.read_pos]
        return result

    def load_next(self):
        self.buffer = []
        # buffering=0 disables buffering, it is desired, because buffering
        # is implemented here, in code
        file = open(self.file_path, "rb", buffering=0)
        file.seek(self.file_pos)
        bytes_to_read = min(
            BYTES_BUFFER_SIZE,
            self.file_size - self.file_pos
        )
        temp_buffer = file.read(bytes_to_read)

        if len(temp_buffer) % RECORD_BYTES_SIZE != 0:
            raise Exception("Read bytes are not multiply of record size")

        self.file_pos += bytes_to_read
        self.loaded_size = bytes_to_read / RECORD_BYTES_SIZE

        temp_ints = list(temp_buffer)

        for i in range(len(temp_buffer) // RECORD_BYTES_SIZE):
            record_ints = temp_ints[
                          RECORD_BYTES_SIZE * i:RECORD_BYTES_SIZE * (i + 1)
                          ]
            self.buffer.append(Record.load_from_ints(record_ints))

        file.close()
        self.disk_reads_count += 1

    def __iter__(self):
        return self

    def __next__(self):
        next_record = self.read_next()
        if next_record is None:
            raise StopIteration
        return next_record


class WriteBuffer:
    def __init__(self, file_path, append_mode=False):
        self.write_pos = 0
        self.size = BUFFER_SIZE
        self.buffer = [None] * BUFFER_SIZE
        self.file_path = file_path
        if not append_mode and os.path.isfile(file_path):
            os.remove(file_path)
        self.runs_written = 0
        self.last_written = None
        self.disk_writes_count = 0

    def write_next(self, record):
        if record < self.last_written:
            self.runs_written += 1
        if self.write_pos == self.size:
            self.flush()
        self.buffer[self.write_pos] = record
        self.write_pos += 1
        self.last_written = record

    def save_next(self):
        ints_to_write = []
        for record in self.buffer[0:self.write_pos]:
            ints_to_write += record.save_to_ints()  # type: ignore

        file = open(self.file_path, "ab", buffering=0)
        file.write(bytearray(ints_to_write))
        file.close()
        self.disk_writes_count += 1

    def flush(self):
        if self.write_pos > 0:
            self.save_next()
            self.write_pos = 0


class Record:
    def __init__(self, items):
        self.items = items

    @staticmethod
    def load_from_ints(record_ints):
        set_length = record_ints[0]
        set_items = record_ints[1:set_length + 1]
        return Record(set_items)

    def save_to_ints(self):
        result = [len(self.items), *self.items]
        zeropad = [0] * (RECORD_BYTES_SIZE - len(result))
        result += zeropad
        return result

    def __repr__(self):
        return f"Zbiór {sorted(self.items, reverse=True)}"

    def __lt__(self, other):
        if other is None:
            return True

        self_items_copy = self.items[:]
        other_items_copy = other.items[:]

        for item in self_items_copy:
            if item in other_items_copy:
                self_items_copy.remove(item)
                other_items_copy.remove(item)

        if len(other_items_copy) == 0:
            return False
        elif len(self_items_copy) == 0:
            return True

        s_max = max(self_items_copy)
        o_max = max(other_items_copy)

        return o_max > s_max


class RunIterator:
    def __init__(self, read_buffer):
        self.read_buffer = read_buffer
        self.current_record = None
        self.end_of_run = False

    def read_next(self):
        if self.end_of_run:
            return None

        self.current_record = self.read_buffer.read_next()

        if self.current_record is None:
            return None

        next_record = self.read_buffer.peek()
        if next_record is not None and next_record < self.current_record:
            self.end_of_run = True

        return self.current_record

    def __iter__(self):
        return self

    def __next__(self):
        res_record = self.read_next()
        if res_record is None:
            raise StopIteration
        return res_record


def print_tape(file_name):
    print(f"[ .. ] Taśma {file_name}\n")

    buffer = ReadBuffer(file_name)
    series_count = 0
    records_count = 0

    while buffer.has_more():
        ri = RunIterator(buffer)
        for record in ri:
            print(record)
            records_count += 1
        series_count += 1
        print("~ koniec biegu ~")

    print(f"\n[ ^- ] Liczba biegów: {series_count}")
    print(f"[ ^- ] Liczba rekordów: {records_count}")


def print_runs(file_name, n):
    print(f"Printing first {n} runs from {file_name}")
    buff = ReadBuffer(file_name)
    for i in range(n):
        print(f"\nRun {i}:")
        ri = RunIterator(buff)
        for record in ri:
            print(record)


def runs_count(file_name):
    rc = 0
    buff = ReadBuffer(file_name)
    while buff.has_more():
        ri = RunIterator(buff)
        for _ in ri:
            pass
        rc += 1
    return rc


# ==============================================================================

def prepare_tapes():
    t1_dest = WriteBuffer("fs/t1")
    for record in ReadBuffer("fs/start_tape"):
        t1_dest.write_next(record)
    t1_dest.flush()

    if os.path.isfile("fs/t2"):
        os.remove("fs/t2")
    if os.path.isfile("fs/t3"):
        os.remove("fs/t3")


class MetaInfo:
    def __init__(self, reads_count, writes_count, runs_count):
        self.reads_count = reads_count
        self.writes_count = writes_count
        self.runs_count = runs_count


def distribute(source_tape_path, first_dest_path, second_dest_path):
    t1_buffer = ReadBuffer(source_tape_path)
    t2_buffer = WriteBuffer(first_dest_path)
    t3_buffer = WriteBuffer(second_dest_path)

    last_record = t1_buffer.read_next()
    t2_buffer.write_next(last_record)
    dest_buffer = t2_buffer

    i = 0
    for record in t1_buffer:
        # Not sorted pair of records
        if record < last_record:
            # Toggle
            if dest_buffer == t2_buffer:
                dest_buffer = t3_buffer
            else:
                dest_buffer = t2_buffer
            i += 1

        if dest_buffer == t2_buffer:
            t2_buffer.write_next(record)
        else:
            t3_buffer.write_next(record)

        last_record = record

    t2_buffer.flush()
    t3_buffer.flush()

    return MetaInfo(t1_buffer.disk_reads_count,
                    t2_buffer.disk_writes_count + t3_buffer.disk_writes_count,
                    t2_buffer.runs_written + t3_buffer.runs_written)


# Read runs alternately from t2 and t3 (reading is done 1 record at a time, because we can't read whole run to memory)
# So one run may end and if it happens we need to write remaining records from non-empty run
# If any of t2 or t3 ends then just write all remaining runs from non-empty tape to t1
# For each two runs merge their records creating new run
# Write that run to t1

def merge_runs(rit1, rit2, write_buffer: WriteBuffer):
    rit1_curr = rit1.read_next()
    rit2_curr = rit2.read_next()
    while rit1_curr is not None and rit2_curr is not None:
        if rit1_curr < rit2_curr:
            write_buffer.write_next(rit1_curr)
            rit1_curr = rit1.read_next()
        else:
            write_buffer.write_next(rit2_curr)
            rit2_curr = rit2.read_next()
    if rit1_curr is not None:
        write_buffer.write_next(rit1_curr)
        for r in rit1:
            write_buffer.write_next(r)
    if rit2_curr is not None:
        write_buffer.write_next(rit2_curr)
        for r in rit2:
            write_buffer.write_next(r)


def merge(first_source_path, second_source_path, dest_tape_path):
    t1_buffer = WriteBuffer(dest_tape_path)
    t2_buffer = ReadBuffer(first_source_path)
    t3_buffer = ReadBuffer(second_source_path)

    while t2_buffer.has_more() and t3_buffer.has_more():
        merge_runs(RunIterator(t2_buffer), RunIterator(t3_buffer), t1_buffer)

    for r in t2_buffer:
        t1_buffer.write_next(r)

    for r in t3_buffer:
        t1_buffer.write_next(r)

    t1_buffer.flush()
    return MetaInfo(t2_buffer.disk_reads_count + t3_buffer.disk_reads_count,
                    t1_buffer.disk_writes_count,
                    t1_buffer.runs_written)


class SortInfo:
    def __init__(self, reads_count, writes_count, phases_count):
        self.reads_count = reads_count
        self.writes_count = writes_count
        self.phases_count = phases_count


def tape_sort(tape_path, print_after_phase=False):
    runs_written = 0
    phases_count = 0
    reads_count = 0
    writes_count = 0
    while runs_written != 1:
        dist_info = distribute(tape_path, "fs/t2", "fs/t3")
        merge_info = merge("fs/t2", "fs/t3", tape_path)
        runs_written = merge_info.runs_count

        reads_count += dist_info.reads_count
        reads_count += merge_info.reads_count
        writes_count += dist_info.writes_count
        writes_count += merge_info.writes_count

        if print_after_phase:
            print(f"[ -v ] Faza {phases_count + 1}")
            print_tape(tape_path)
        print(f"[ .. ] {runs_written} biegów pozostało")
        phases_count += 1

    return SortInfo(reads_count, writes_count, phases_count)

help_page = """
pomoc
    wyświetla tę stronę
wyczyść <ścieżka_do_taśmy>
    usuwa taśmę
genlos <ścieżka_do_taśmy> <liczba_rekordów> [opcje]
    dopisuje losowo wygenerowane rekordy na taśmę
        jeżeli jako opcja podane zostanie 'o', wówczas taśma zostanie nadpisana
        nowowygenerowanymi rekordami
dopisz <ścieżka_do_taśmy> <liczba, ...>
    dopisuje nowy rekord na koniec taśmy, jako
    <liczba, ...> należy podać co najmniej 1 liczbę, a
    maksymalnie 15, każdą z zakresu 0-255
wczytaj <ścieżka_do_taśmy> <ścieżka_do_pliku>
    wczytuje rekordy z podanego pliku testowego na taśmę
sortuj <ścieżka_do_taśmy> [opcje]
    sortuje podaną taśmę wypisując jej zawartość na
    początku i na końcu operacji.
        Gdy zostanie podana opcja 'v', wówczas taśma będzie
        wyświetlana po każdej z faz
wyświetl <ścieżka_do_taśmy>
    wyświetla zawartość taśmy i jej metadane m.in.:
        liczbę biegów (serii)
        liczbę rekordów
"""

print("\nProjekt SBD - sortowanie metodą scalania naturalnego (2+1)")
print("Autor: Maciej Krzyżanowski [188872]\n")
should_run = True
while should_run:
    cmd_line = input("> ")
    match cmd_line.split():
        case ["wyczyść", tape_path]:
            print(f"[ .. ] Czyszczenie taśmy {tape_path}")
            if os.path.isfile(tape_path):
                os.remove(tape_path)
                print(f"[ :) ] Wyczyszczono taśmę")
            else:
                print(f"[ :( ] Taśma o podanej ścieżce nie istnieje")
        case ["genlos", tape_path, number_of_records, *options]:
            if "o" in options: 
                write_buffer = WriteBuffer(tape_path)
            else:
                write_buffer = WriteBuffer(
                    tape_path, append_mode=True)
            for i in range(int(number_of_records)):
                set_length = randint(1, 15)
                new_set = []
                while len(new_set) != set_length:
                    new_suggestion = randint(0, 255)
                    if new_suggestion not in new_set:
                        new_set.append(new_suggestion)
                new_record = Record(new_set)
                write_buffer.write_next(new_record)
            write_buffer.flush()
            print(f"[ :) ] Dopisano {number_of_records} nowych rekordów do " +
                  f"taśmy {tape_path}")
        case ["wyświetl", tape_path]:
            print(f"[ :) ] Wyświetlam taśmę {tape_path}")
            print_tape(tape_path)
        case ["dopisz", tape_path, *set_elements]:
            if len(set_elements) == 0:
                print("[ :( ] Nie podano ani jednego rekordu")
                continue
            set_elements = [int(x) for x in set_elements]
            new_record = Record(set_elements)
            write_buffer = WriteBuffer(tape_path, append_mode=True)
            write_buffer.write_next(new_record)
            write_buffer.flush()
            print(f"[ :) ] Dopisano podany rekord na taśmę")
        case ["sortuj", tape_path, *options]:
            print(f"[ .. ] Sortowanie taśmy {tape_path}")
            print(f"[ -v ] Wyświetlam taśmę przed posortowaniem:")
            print_tape(tape_path)
            if "v" in options:
                sort_info = tape_sort(tape_path, print_after_phase=True)
            else:
                sort_info = tape_sort(tape_path)
            print(f"[ -v ] Wyświetlam taśmę po posortowaniu:")
            print_tape(tape_path)
            print(f"[ :) ] Taśma {tape_path} posortowana!")
            print(f"[ -v ] Metadane sortowania")
            print(f"[ .. ] Liczba faz {sort_info.phases_count}")
            print(f"[ .. ] Liczba odczytów {sort_info.reads_count}")
            print(f"[ .. ] Liczba zapisów {sort_info.writes_count}")
        case ["wczytaj", tape_path, test_file_path]:
            wb = WriteBuffer(tape_path, append_mode=True)
            count = 0
            with open(test_file_path) as test_file:
                for line in test_file:
                    set_numbers = [int(s) for s in line.rstrip().split()]
                    new_record = Record(set_numbers)
                    wb.write_next(new_record)
                    count += 1
            wb.flush()
            print(f"[ :) ] Dopisano {count} rekordów na taśmę")
        case ["pomoc"]:
            print(help_page)
        case ["wyjście"]:
            print("[ :) ] Do widzenia!")
            should_run = False
        case _:
            print("[ :( ] Nie znam takiej komendy")

