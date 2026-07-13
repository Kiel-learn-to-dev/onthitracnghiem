"""Apply source-backed repairs for OCR rows whose choices were split by OCR."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


REPAIRS = {
    650: (["fread(ptr,size,file,n)", "fread(file,ptr,size,n)", "fread(size,ptr,n,file)", "fread(ptr,size,n,file)"], "D", "Course prototype order is pointer, size, count, file."),
    655: (["Open binary for writing", "Open existing binary and append", "Open new binary for writing", "Open binary for reading"], "B", "ab is append-binary mode."),
    656: (["double chsize", "long chsize", "int chsize", "All above"], "C", "The course prototype returns int."),
    658: (["Open text for writing", "Open text for reading", "Open text for read and write", "Open existing text for reading"], "C", "r+ is read/write mode."),
    661: (["%hi", "%hu", "%i", "%lu"], "A", "The course uses %hi for short int."),
    668: (["Undefined", "0", "1", "2"], "B", "Unspecified aggregate elements are zero-initialized."),
    671: (["[0,100]", "[0,99]", "[1,100]", "[1,99]"], "B", "An array of 100 elements uses indices 0 through 99."),
    674: (["O(n)", "O(n^2)", "O(n log n)", "O(1)"], "B", "Bubble sort has quadratic average complexity."),
    675: (["Binary search", "Sequential search", "Vector search", "Linear search"], "D", "Linear search is a search algorithm."),
    678: (["int[][] arr;", "int[20] arr[20];", "int arr[20][];", "int arr[20][20];"], "D", "Both dimensions need bounds in this declaration."),
    679: (["m elements", "n elements", "m+n elements", "m*n elements"], "D", "An m by n array contains m*n elements."),
    680: (["arr=[0][0]=10;", "arr[0,0]=10;", "arr[0][0]=1025;", "arr[0][0]=NULL;"], "C", "arr[0][0] is an int element."),
    687: (["Program copies argument and passes copy.", "Program passes current variable.", "Program passes address.", "Program copies then passes original."], "A", "Pass by value uses a copy."),
    689: (["return changes one value.", "Reference changes several values.", "return changes several and reference one.", "A and B false."], "B", "References permit multiple outputs."),
    691: (["swap(a,b);", "swap(a,&b);", "swap(&a,b);", "swap(&a,&b);"], "D", "The prototype requires two pointers."),
    695: (["&&", "||", "!", "Other operator."], "B", "Logical OR is ||."),
    701: (["Signed stores both but unsigned only negative.", "Signed stores both but unsigned only nonnegative.", "Signed stores Vietnamese letters.", "Signed only positive, unsigned negative."], "B", "Unsigned represents a nonnegative range."),
    705: (["H", "e", "l", "n"], "B", "Helen index 3 is e."),
    712: (["A constant", "A value", "A variable", "A type"], "C", "A reference argument is normally a variable."),
    713: (["int", "float", "void", "double"], "C", "A function without a return value has void return type."),
}


def main() -> None:
    database = Path(__file__).resolve().parent.parent / "data" / "review.db"
    connection = sqlite3.connect(database)
    with connection:
        for question_id, (choices, answer, solution) in REPAIRS.items():
            connection.execute(
                """UPDATE source_questions
                   SET raw_choices_json=?, proposed_answer=?, solution=?,
                       answer_status='solved', extraction_status='approved',
                       answer_reason='Reconstructed from OCR content and course convention; concept checked.'
                   WHERE id=?""",
                (json.dumps(choices, ensure_ascii=False), answer, solution, question_id),
            )
    print(f"Updated {len(REPAIRS)} questions.")


if __name__ == "__main__":
    main()
