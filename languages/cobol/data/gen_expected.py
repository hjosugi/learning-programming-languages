#!/usr/bin/env python3
"""Simulate the exact COBOL edited-PIC output of src/payroll.cob.

NOT part of the shipped program. A one-off authoring helper used to derive
expected_output.txt byte-for-byte while GnuCOBOL (cobc) is unavailable on the
authoring machine. The COBOL program is the source of truth; this mirrors its
ANSI/ISO numeric-editing rules (floating '$', 'Z' suppression, '*' check
protection, comma/decimal insertion, 'CR' on negatives).
"""
from decimal import Decimal, ROUND_HALF_UP


def fmt_pic(picture: str, value: Decimal) -> str:
    """Format a Decimal per a (subset of) COBOL numeric-edited PICTURE.

    Output width always equals the number of character positions in the
    picture (with CR counting as 2), so columns align exactly like cobc.

    Integer-part families supported:
      * Z / *  zero suppression (space / check-protection fill)
      * floating '$'  (e.g. $$$,$$9.99): n '$' => n-1 digit positions
      * fixed '$'     (e.g. $*,***,**9.99): single leading literal '$'
      * insertion ',' and '.', forced digit '9', trailing 'CR'
    """
    cr = picture.endswith("CR")
    pic = picture[:-2] if cr else picture
    negative = value < 0

    int_pic, _, dec_pic = pic.partition(".")
    dec_count = len(dec_pic)
    quant = Decimal(1).scaleb(-dec_count) if dec_count else Decimal(1)
    av = abs(value).quantize(quant, rounding=ROUND_HALF_UP)
    int_part = int(av)

    n_dollar = int_pic.count("$")
    floating_dollar = n_dollar > 1
    fixed_dollar = int_pic.startswith("$") and n_dollar == 1
    has_star = "*" in int_pic
    positions = list(int_pic)

    # Number of digit positions the picture can show.
    if floating_dollar:
        capacity = (n_dollar - 1) + sum(1 for c in positions if c == "9")
    elif fixed_dollar:
        capacity = sum(1 for c in positions if c in "9Z*")
    else:
        capacity = sum(1 for c in positions if c in "9Z*$")

    digits = str(int_part)
    if len(digits) > capacity:
        digits = digits[-capacity:]
    digits = digits.rjust(capacity)  # leading spaces mark suppressed zeros

    # Pass 1: right-to-left, drop each digit into a digit-bearing symbol.
    rendered = [None] * len(positions)
    dptr = len(digits) - 1
    for i in range(len(positions) - 1, -1, -1):
        ch = positions[i]
        if ch in "9Z*$":
            rendered[i] = digits[dptr] if dptr >= 0 else " "
            dptr -= 1
        else:
            rendered[i] = ch

    # Leftmost significant digit position (drives suppression & comma logic).
    first_sig = None
    for i, ch in enumerate(positions):
        if ch in "9Z*$" and rendered[i] != " ":
            first_sig = i
            break
    if "9" in int_pic:  # a forced 9 is significant even for a zero value
        nine_idx = int_pic.index("9")
        if first_sig is None or nine_idx < first_sig:
            first_sig = nine_idx

    out = []
    for i, ch in enumerate(positions):
        if ch in "9Z*$":
            if first_sig is not None and i >= first_sig:
                d = rendered[i]
                out.append(d if d != " " else "0")
            else:
                out.append("*" if has_star else " ")
        elif ch == ",":
            if first_sig is not None and i > first_sig:
                out.append(",")
            else:
                out.append("*" if has_star else " ")
        else:
            out.append(ch)
    int_render = "".join(out)

    # Place the currency sign.
    if floating_dollar:
        if first_sig is not None and first_sig > 0:
            int_render = int_render[:first_sig - 1] + "$" + int_render[first_sig:]
        elif first_sig == 0:
            int_render = "$" + int_render[1:]
    elif fixed_dollar:
        didx = int_pic.index("$")
        int_render = int_render[:didx] + "$" + int_render[didx + 1:]

    if dec_count:
        frac_str = f"{av - int_part:.{dec_count}f}".split(".")[1]
        result = int_render + "." + frac_str
    else:
        result = int_render

    if cr:
        result += "CR" if negative else "  "
    return result


# ---- Reproduce the payroll computation exactly. --------------------------
def r2(x):
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_report():
    emps = [
        (1001, "Ada Lovelace",      "ENG", Decimal("42.50"), Decimal("44.00")),
        (1002, "Grace Hopper",      "ENG", Decimal("55.00"), Decimal("40.00")),
        (1003, "Katherine Johnson", "SCI", Decimal("48.00"), Decimal("52.00")),
        (1004, "Alan Turing",       "SCI", Decimal("60.00"), Decimal("38.00")),
        (1005, "Edsger Dijkstra",   "ENG", Decimal("50.00"), Decimal("0.00")),
        (1006, "Margaret Hamilton", "SCI", Decimal("47.25"), Decimal("45.50")),
    ]
    STD = Decimal("40.00")
    OT = Decimal("1.5")
    tot_gross = tot_tax = tot_net = tot_hours = Decimal(0)
    paid = 0
    bar_eq = "=" * 75
    bar_dash = "-" * 75
    L = [
        bar_eq,
        "                    ACME CORP - WEEKLY PAYROLL REPORT",
        bar_eq,
        "  ID    NAME                DEPT  HOURS      GROSS        TAX          NET",
        bar_dash,
    ]
    for (eid, name, dept, rate, hours) in emps:
        if hours > STD:
            reg, oth = STD, hours - STD
        else:
            reg, oth = hours, Decimal(0)
        reg_pay = reg * rate
        ot_pay = r2(oth * rate * OT)
        gross = reg_pay + ot_pay
        if gross == 0:
            trate = Decimal("0.0000")
        elif gross <= 1000:
            trate = Decimal("0.1000")
        elif gross <= 2000:
            trate = Decimal("0.2000")
        else:
            trate = Decimal("0.3000")
        tax = r2(gross * trate)
        net = gross - tax
        tot_gross += gross
        tot_tax += tax
        tot_net += net
        tot_hours += hours
        if hours > 0:
            paid += 1
        L.append(
            "  " + f"{eid:04d}" + "  " + name.ljust(18)[:18] + dept.ljust(5)[:5]
            + fmt_pic("ZZ9.99", hours) + "  "
            + fmt_pic("$$$,$$9.99", gross) + "  "
            + fmt_pic("$$$,$$9.99", tax) + "  "
            + fmt_pic("$$$,$$9.99", net)
        )
    L.append(bar_dash)
    L.append(
        "  GRAND TOTALS".ljust(31)
        + fmt_pic("ZZ9.99", tot_hours) + "  "
        + fmt_pic("$$$,$$9.99", tot_gross) + "  "
        + fmt_pic("$$$,$$9.99", tot_tax) + "  "
        + fmt_pic("$$$,$$9.99", tot_net)
    )
    L.append(bar_eq)
    avg = r2(tot_net / paid) if paid else Decimal(0)
    adj = tot_net - tot_net
    L.append("  EMPLOYEES PAID:   " + fmt_pic("Z,ZZ9", Decimal(paid)))
    L.append("  AVERAGE NET PAY:  " + fmt_pic("$*,***,**9.99", avg))
    L.append("  ROUNDING ADJUST:  " + fmt_pic("$$$,$$9.99CR", adj))
    L.append(bar_eq)
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        cases = [
            ("$$$,$$9.99", "0", "     $0.00"),
            ("$$$,$$9.99", "1955.00", " $1,955.00"),
            ("$$$,$$9.99", "391.00", "   $391.00"),
            ("$$$,$$9.99", "11498.81", "$11,498.81"),
            ("$$$,$$9.99", "835.20", "   $835.20"),
            ("ZZ9.99", "44.00", " 44.00"),
            ("ZZ9.99", "0.00", "  0.00"),
            ("ZZ9.99", "219.50", "219.50"),
            ("Z,ZZ9", "5", "    5"),
            ("$*,***,**9.99", "1648.93", "$****1,648.93"),
            ("$$$,$$9.99CR", "0", "     $0.00  "),
            ("$$$,$$9.99CR", "-12.34", "    $12.34CR"),
        ]
        ok = True
        for pic, val, exp in cases:
            got = fmt_pic(pic, Decimal(val))
            good = got == exp
            ok = ok and good
            print(f"{'OK ' if good else 'BAD'} {pic:14} {val:9} [{got}] (len {len(got)}) exp [{exp}]")
        print("ALL OK" if ok else "FAILURES")
        sys.exit(0 if ok else 1)
    sys.stdout.write(build_report())
