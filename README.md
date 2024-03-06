# :recycle: Natural Merge Sort
Program implementing 2+1 variant of natural merge sort algorithm. It allows to perform some manipulation of tapes like generating and writing new random records, clearing a tape, writing single given record or displaying its contents - and finally sorting tapes. Tapes are just files on a disk in which records are saved.

This algorithm (generally, algorithms of this kind) may be used in some database engine implementation, because it allows sorting any amount of records, regardless of the RAM available - it only needs memory for 3 buffers (1536 bytes).

Computational complexity of this algorithm is **approx.** $\frac{4N\lceil{log_2r}\rceil}{b}$, where N is number of records at the beginning, r is number of series at the beginning and b is blocking factor (how many records may fit in buffer).

This implementation operates on records which are sets of maximum 15 numbers (in range 0-255).

**Sorting condition**
A > B if after removing all common records from A and B, maximum number from A is bigger than maximum number from B.

## Algorithm explanation
2+1 method uses 3 tapes (t1, t2, t3) to sort the file, 2 for read (t2, t3) and 1 for write (t1, merge phase) or 1 for read (t1) and 2 for write (t2, t3, distribute phase). To minimize disk read/writes 3 buffers are used - 1 for each of tapes. Each of buffers are of 32 records size = 512 bytes, so any disk operation is reading or writing 512 bytes from/to disk.

1. Read consecutive series from t1 and write them alternatively to t1 and t2 (distribute phase)
2. Get two series, one from t2 and one from t3 tape (merge phase)
	1. If there is end of t2 or t3 (t2 or t3 is empty) then rewrite the non-empty of tapes to t1 and go to 3.
	2. Merge these series, iteratively taking smaller of records from t2 and t3 and writing it to t1. For performance reasons is is checked if record written to t1 is in order and if not - series counter is incremented (so to know how many series are on t1)
3. Check if series counter is 1 and if not then go back to step 1.

## Commands
- help
	- displays the help page
- clear <path_to_tape>
	- clears/deletes a tape
	- Example: clear fs/t1
- genrandom <path_to_tape> <record_count> [options]
	- adds record_count random records at the end of the tape
	- if 'o' is provided as an option then tape is overwritten with these newly generated random records
	- Example: genrandom fs/t1 30 o
- add <path_to_tape> <numbers, ...>
    - adds new record (set created from 1 to 15 numbers in range 0-255) at the
      end of the tape
    - Example: add fs/t1 7 25 3 4 5
- load <path_to_tape> <path_to_test_file>
	- adds the records described in test file to the tape
	- Example: load fs/t1 fs/testfile
- sort <path_to_tape> [options]
	- sorts the provided tape displaying its contents before and after sorting. When option 'v' is provided then tape will be displayed after each phase
	- Example: sort fs/t1 v
- display <path_to_tape>
	- displays the tape's records and information how many series and records it contains. Also when displaying records it is shown when each of series end
	- Example: display fs/t1
- exit
	- exists program gracefully

## Test file format

```
10 9 8 7
9 8 7 6
12 11 10 9
8 7 6 5
15 14 13 12
14 13 12 11
18 17 16 15
13 12 11 10
```
:point_up: Exemplary test file

Each line represents one record. As in this project record is set of numbers, then each line represents one set and numbers on this line are numbers in the set

## Running
Program (naturalmerge.py) should be run using Python 3, it does not need any external libraries.

dump.sh may be used to display hex values stored in t1, t2, t3 tapes - it was
useful mainly for debugging :)
