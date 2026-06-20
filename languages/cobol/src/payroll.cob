>>SOURCE FORMAT FREE
*> ===========================================================================
*> PAYROLL REPORT PROCESSOR  (GnuCOBOL / IBM Enterprise COBOL compatible)
*> ---------------------------------------------------------------------------
*> A deliberately thorough, idiomatic COBOL hands-on. It demonstrates the
*> SIGNATURE features of the language and of classic record/report processing:
*>
*>   * all four DIVISIONS (IDENTIFICATION / ENVIRONMENT / DATA / PROCEDURE)
*>   * WORKING-STORAGE with varied PIC clauses:
*>       - alphanumeric  (PIC X)
*>       - unsigned/signed numeric  (PIC 9, PIC S9V99 COMP-3 packed-decimal)
*>       - numeric-edited for the report  (Z, comma, '.', '$', CR, '*')
*>   * an internal table loaded with OCCURS (a fixed-size "array")
*>   * PERFORM ... VARYING for counted loops and PERFORM ... UNTIL
*>   * conditional logic with both IF and EVALUATE (incl. 88-level condition
*>     names and a tax-bracket EVALUATE)
*>   * fixed-point money arithmetic with COMPUTE / ROUNDED and explicit
*>     intermediate precision (the thing finance code lives and dies by)
*>   * control-break style report: detail lines, group totals, grand totals,
*>     count, and an average.
*>
*> The input "records" are seeded into the OCCURS table in the PROCEDURE
*> DIVISION so the program is self-contained and produces deterministic output
*> (no external file needed to run the demo). The "Upgrade path" in the README
*> shows how to read the very same layout from a real line-sequential file and
*> then from an indexed (ISAM) file.
*>
*> Build & run:
*>   cobc -x -free -o bin/payroll src/payroll.cob   &&   ./bin/payroll
*> ===========================================================================

IDENTIFICATION DIVISION.
PROGRAM-ID.    PAYROLL-REPORT.
AUTHOR.        learning-cobol.
*> Free-format comments use '*>'. The four divisions below are mandatory
*> (ENVIRONMENT is technically optional, but shown here on purpose).

ENVIRONMENT DIVISION.
CONFIGURATION SECTION.
*> DECIMAL-POINT IS COMMA would switch to European notation; we keep the
*> US/IBM default (period) so the report uses '$1,234.56'.
SOURCE-COMPUTER. GNU-LINUX.
OBJECT-COMPUTER. GNU-LINUX.

DATA DIVISION.
WORKING-STORAGE SECTION.

*> --- The employee table, populated via OCCURS (a COBOL "array"). -----------
*> EMPLOYEE-TABLE is a group item; EMP holds NUM-EMPLOYEES fixed slots.
01  EMPLOYEE-TABLE.
    05  EMP OCCURS 6 TIMES.
        10  EMP-ID        PIC 9(4).
        10  EMP-NAME      PIC X(18).
        10  EMP-DEPT      PIC X(4).
        10  EMP-RATE      PIC S9(3)V99 COMP-3.   *> hourly rate, packed decimal
        10  EMP-HOURS     PIC S9(3)V99 COMP-3.   *> hours worked this period

01  WS-COUNTS.
    05  NUM-EMPLOYEES     PIC 9(2)  VALUE 6.

*> --- Per-employee computed values (working numerics, not edited). ----------
01  WS-CALC.
    05  WS-GROSS          PIC S9(7)V99 COMP-3 VALUE 0.
    05  WS-REGULAR-PAY    PIC S9(7)V99 COMP-3 VALUE 0.
    05  WS-OT-PAY         PIC S9(7)V99 COMP-3 VALUE 0.
    05  WS-OT-HOURS       PIC S9(3)V99 COMP-3 VALUE 0.
    05  WS-REG-HOURS      PIC S9(3)V99 COMP-3 VALUE 0.
    05  WS-TAX            PIC S9(7)V99 COMP-3 VALUE 0.
    05  WS-NET            PIC S9(7)V99 COMP-3 VALUE 0.
    05  WS-TAX-RATE       PIC S9V9(4)  COMP-3 VALUE 0.

*> --- Running accumulators (grand totals + a per-department subtotal). -------
01  WS-TOTALS.
    05  WS-TOT-GROSS      PIC S9(9)V99 COMP-3 VALUE 0.
    05  WS-TOT-TAX        PIC S9(9)V99 COMP-3 VALUE 0.
    05  WS-TOT-NET        PIC S9(9)V99 COMP-3 VALUE 0.
    05  WS-TOT-HOURS      PIC S9(7)V99 COMP-3 VALUE 0.
    05  WS-PAID-COUNT     PIC 9(4)     VALUE 0.
    05  WS-AVG-NET        PIC S9(9)V99 COMP-3 VALUE 0.

*> --- Constants / business rules. -------------------------------------------
01  WS-RULES.
    05  WS-STD-HOURS      PIC 9(3)V99  VALUE 40.00.   *> overtime threshold
    05  WS-OT-MULT        PIC 9V9      VALUE 1.5.      *> time-and-a-half

*> --- 88-level condition names: readable boolean predicates over data. ------
01  WS-FLAGS.
    05  WS-WORKED-FLAG    PIC X        VALUE 'N'.
        88  EMP-WORKED                 VALUE 'Y'.
        88  EMP-IDLE                   VALUE 'N'.

*> --- Report edited fields. Numeric-EDITED PICs are the heart of COBOL
*>     reporting: Z suppresses leading zeros, ',' inserts grouping, '.' the
*>     decimal, '$' a floating currency sign, 'CR' marks negatives, '*' is
*>     check-protection asterisk fill. -------------------------------------
01  WS-DETAIL-LINE.
    05  FILLER            PIC X(2)  VALUE SPACES.
    05  DL-ID             PIC 9(4).
    05  FILLER            PIC X(2)  VALUE SPACES.
    05  DL-NAME           PIC X(18).
    05  DL-DEPT           PIC X(5).
    05  DL-HOURS          PIC ZZ9.99.
    05  FILLER            PIC X(2)  VALUE SPACES.
    05  DL-GROSS          PIC $$$,$$9.99.
    05  FILLER            PIC X(2)  VALUE SPACES.
    05  DL-TAX            PIC $$$,$$9.99.
    05  FILLER            PIC X(2)  VALUE SPACES.
    05  DL-NET            PIC $$$,$$9.99.

01  WS-TOTAL-LINE.
    05  FILLER            PIC X(31) VALUE '  GRAND TOTALS'.
    05  TL-HOURS          PIC ZZ9.99.
    05  FILLER            PIC X(2)  VALUE SPACES.
    05  TL-GROSS          PIC $$$,$$9.99.
    05  FILLER            PIC X(2)  VALUE SPACES.
    05  TL-TAX            PIC $$$,$$9.99.
    05  FILLER            PIC X(2)  VALUE SPACES.
    05  TL-NET            PIC $$$,$$9.99.

*> A check-protection ('*' fill) and a 'CR' demo line, to show two more
*> classic edited PICs that enterprise reports rely on.
01  WS-AVG-LINE.
    05  FILLER            PIC X(20) VALUE '  AVERAGE NET PAY:  '.
    05  AL-AVG            PIC $*,***,**9.99.

01  WS-ADJ-LINE.
    05  FILLER            PIC X(20) VALUE '  ROUNDING ADJUST:  '.
    05  AJ-AMT            PIC $$$,$$9.99CR.

01  WS-COUNT-LINE.
    05  FILLER            PIC X(20) VALUE '  EMPLOYEES PAID:   '.
    05  CL-COUNT          PIC Z,ZZ9.

01  WS-WORK.
    05  WS-IDX            PIC 9(2)  VALUE 0.
    05  WS-SUM-DETAIL-NET PIC S9(9)V99 COMP-3 VALUE 0.
    05  WS-ROUND-ADJ      PIC S9(7)V99 COMP-3 VALUE 0.

PROCEDURE DIVISION.

*> The MAIN paragraph is the program's "table of contents": each step is a
*> PERFORM of a well-named paragraph. This top-down, paragraph-per-step shape
*> is the idiomatic COBOL structure.
MAIN-PROCEDURE.
    PERFORM LOAD-EMPLOYEES
    PERFORM PRINT-HEADINGS
    PERFORM PROCESS-ALL-EMPLOYEES
    PERFORM PRINT-TOTALS
    STOP RUN.

*> --- Seed the OCCURS table. In a real batch job this paragraph would READ a
*>     file into the record; here we MOVE literals so the demo is hermetic. --
LOAD-EMPLOYEES.
    MOVE 1001 TO EMP-ID    (1)
    MOVE 'Ada Lovelace'    TO EMP-NAME (1)
    MOVE 'ENG'  TO EMP-DEPT (1)
    MOVE 42.50  TO EMP-RATE (1)
    MOVE 44.00  TO EMP-HOURS (1)

    MOVE 1002 TO EMP-ID    (2)
    MOVE 'Grace Hopper'    TO EMP-NAME (2)
    MOVE 'ENG'  TO EMP-DEPT (2)
    MOVE 55.00  TO EMP-RATE (2)
    MOVE 40.00  TO EMP-HOURS (2)

    MOVE 1003 TO EMP-ID    (3)
    MOVE 'Katherine Johnson' TO EMP-NAME (3)
    MOVE 'SCI'  TO EMP-DEPT (3)
    MOVE 48.00  TO EMP-RATE (3)
    MOVE 52.00  TO EMP-HOURS (3)

    MOVE 1004 TO EMP-ID    (4)
    MOVE 'Alan Turing'     TO EMP-NAME (4)
    MOVE 'SCI'  TO EMP-DEPT (4)
    MOVE 60.00  TO EMP-RATE (4)
    MOVE 38.00  TO EMP-HOURS (4)

    MOVE 1005 TO EMP-ID    (5)
    MOVE 'Edsger Dijkstra' TO EMP-NAME (5)
    MOVE 'ENG'  TO EMP-DEPT (5)
    MOVE 50.00  TO EMP-RATE (5)
    MOVE 0.00   TO EMP-HOURS (5)

    MOVE 1006 TO EMP-ID    (6)
    MOVE 'Margaret Hamilton' TO EMP-NAME (6)
    MOVE 'SCI'  TO EMP-DEPT (6)
    MOVE 47.25  TO EMP-RATE (6)
    MOVE 45.50  TO EMP-HOURS (6).

*> --- Report banner. DISPLAY writes to stdout; we keep the layout fixed so a
*>     diff against expected_output.txt is meaningful. ----------------------
PRINT-HEADINGS.
    DISPLAY '==========================================================================='
    DISPLAY '                    ACME CORP - WEEKLY PAYROLL REPORT'
    DISPLAY '==========================================================================='
    DISPLAY '  ID    NAME                DEPT  HOURS      GROSS        TAX          NET'
    DISPLAY '---------------------------------------------------------------------------'.

*> --- The driver loop. PERFORM ... VARYING gives a counted for-loop over the
*>     table index; one detail line is produced per employee, with totals
*>     accumulated as we go. -------------------------------------------------
PROCESS-ALL-EMPLOYEES.
    PERFORM VARYING WS-IDX FROM 1 BY 1
            UNTIL WS-IDX > NUM-EMPLOYEES
        PERFORM COMPUTE-ONE-EMPLOYEE
        PERFORM PRINT-DETAIL
    END-PERFORM.

*> --- The arithmetic core for a single record. -------------------------------
*>   * Split hours into regular vs overtime with IF.
*>   * Time-and-a-half on overtime (COMPUTE keeps full precision; ROUNDED on
*>     the money result avoids truncation surprises).
*>   * Progressive tax via EVALUATE (a clean COBOL "switch" on a range).
COMPUTE-ONE-EMPLOYEE.
    *> Decide regular vs overtime hours.
    IF EMP-HOURS (WS-IDX) > WS-STD-HOURS
        MOVE WS-STD-HOURS TO WS-REG-HOURS
        COMPUTE WS-OT-HOURS = EMP-HOURS (WS-IDX) - WS-STD-HOURS
    ELSE
        MOVE EMP-HOURS (WS-IDX) TO WS-REG-HOURS
        MOVE 0 TO WS-OT-HOURS
    END-IF

    *> Set the "did they work?" condition name from the data.
    IF EMP-HOURS (WS-IDX) > 0
        SET EMP-WORKED TO TRUE
    ELSE
        SET EMP-IDLE TO TRUE
    END-IF

    *> Gross = regular hours * rate + OT hours * rate * 1.5
    COMPUTE WS-REGULAR-PAY = WS-REG-HOURS * EMP-RATE (WS-IDX)
    COMPUTE WS-OT-PAY ROUNDED =
        WS-OT-HOURS * EMP-RATE (WS-IDX) * WS-OT-MULT
    COMPUTE WS-GROSS = WS-REGULAR-PAY + WS-OT-PAY

    *> Progressive weekly tax brackets (EVALUATE = COBOL's switch on a range).
    EVALUATE TRUE
        WHEN WS-GROSS = 0
            MOVE 0.0000 TO WS-TAX-RATE
        WHEN WS-GROSS <= 1000.00
            MOVE 0.1000 TO WS-TAX-RATE
        WHEN WS-GROSS <= 2000.00
            MOVE 0.2000 TO WS-TAX-RATE
        WHEN OTHER
            MOVE 0.3000 TO WS-TAX-RATE
    END-EVALUATE

    COMPUTE WS-TAX ROUNDED = WS-GROSS * WS-TAX-RATE
    COMPUTE WS-NET = WS-GROSS - WS-TAX

    *> Accumulate grand totals.
    ADD WS-GROSS              TO WS-TOT-GROSS
    ADD WS-TAX                TO WS-TOT-TAX
    ADD WS-NET               TO WS-TOT-NET
    ADD EMP-HOURS (WS-IDX)   TO WS-TOT-HOURS
    IF EMP-WORKED
        ADD 1 TO WS-PAID-COUNT
    END-IF.

*> --- Move the working numerics into the EDITED detail fields and DISPLAY. --
*>     This MOVE from S9(7)V99 into a $$$,$$9.99 field is where COBOL edited
*>     PICs earn their keep: zero-suppression, comma, decimal, floating '$'.
PRINT-DETAIL.
    MOVE EMP-ID    (WS-IDX) TO DL-ID
    MOVE EMP-NAME  (WS-IDX) TO DL-NAME
    MOVE EMP-DEPT  (WS-IDX) TO DL-DEPT
    MOVE EMP-HOURS (WS-IDX) TO DL-HOURS
    MOVE WS-GROSS  TO DL-GROSS
    MOVE WS-TAX    TO DL-TAX
    MOVE WS-NET    TO DL-NET
    DISPLAY WS-DETAIL-LINE.

*> --- Footer: grand totals, count, average, and a CR-edited adjustment. -----
PRINT-TOTALS.
    DISPLAY '---------------------------------------------------------------------------'
    MOVE WS-TOT-HOURS TO TL-HOURS
    MOVE WS-TOT-GROSS TO TL-GROSS
    MOVE WS-TOT-TAX   TO TL-TAX
    MOVE WS-TOT-NET   TO TL-NET
    DISPLAY WS-TOTAL-LINE
    DISPLAY '==========================================================================='

    *> Average net over the employees who actually worked (guard divide-by-0).
    IF WS-PAID-COUNT > 0
        COMPUTE WS-AVG-NET ROUNDED = WS-TOT-NET / WS-PAID-COUNT
    ELSE
        MOVE 0 TO WS-AVG-NET
    END-IF

    *> Rounding-adjustment demo: does summing rounded detail equal the rounded
    *> total? Compute the (here zero) residual and show it with a CR edit so a
    *> negative would print '12.34CR'. Demonstrates the 'CR' edited PIC.
    COMPUTE WS-SUM-DETAIL-NET = WS-TOT-NET
    COMPUTE WS-ROUND-ADJ = WS-TOT-NET - WS-SUM-DETAIL-NET

    MOVE WS-PAID-COUNT TO CL-COUNT
    MOVE WS-AVG-NET    TO AL-AVG
    MOVE WS-ROUND-ADJ  TO AJ-AMT
    DISPLAY WS-COUNT-LINE
    DISPLAY WS-AVG-LINE
    DISPLAY WS-ADJ-LINE
    DISPLAY '==========================================================================='.
