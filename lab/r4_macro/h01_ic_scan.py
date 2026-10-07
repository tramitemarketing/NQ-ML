"""H01-H15: rank-IC fra variazioni/livelli di tassi, curva e dollaro (noti all'apertura) e rendimento NQ
open->open a h sessioni. Griglia piccola e dichiarata qui prima di eseguirla. Unita': rendimento %."""
import json
from lab import core
from lab.r4_macro import common as C

TESTS = [
    ("H01_d1_10y_f1", "d1_DGS10", 1, "variazione 1g del 10 anni -> NQ 1g"),
    ("H02_d5_10y_f5", "d5_DGS10", 5, "variazione 5g del 10 anni -> NQ 5g"),
    ("H03_d20_10y_f20", "d20_DGS10", 20, "variazione 20g del 10 anni -> NQ 20g"),
    ("H04a_d5_3m_f5", "d5_DGS3MO", 5, "variazione 5g del 3 mesi -> NQ 5g"),
    ("H04b_d20_3m_f20", "d20_DGS3MO", 20, "variazione 20g del 3 mesi -> NQ 20g"),
    ("H05a_slope_lvl_f20", "T10Y2Y", 20, "livello pendenza 10a-2a -> NQ 20g"),
    ("H05b_slope_z250_f20", "z250_T10Y2Y", 20, "pendenza z-score 250g -> NQ 20g"),
    ("H06a_dslope5_f5", "d5_T10Y2Y", 5, "variazione 5g pendenza -> NQ 5g"),
    ("H06b_dslope20_f20", "d20_T10Y2Y", 20, "variazione 20g pendenza -> NQ 20g"),
    ("H07_z250_10y_f20", "z250_DGS10", 20, "10 anni z-score 250g (livello relativo) -> NQ 20g"),
    ("H08a_usd1_f1", "r1_USD", 1, "dollaro 1g -> NQ 1g"),
    ("H08b_usd5_f5", "r5_USD", 5, "dollaro 5g -> NQ 5g"),
    ("H08c_usd20_f20", "r20_USD", 20, "dollaro 20g -> NQ 20g"),
    ("H13_d60_10y_f20", "d60_DGS10", 20, "momentum 60g del 10 anni -> NQ 20g"),
    ("H14_3m_lvl_f20", "DGS3MO", 20, "livello 3 mesi (carry del cash) -> NQ 20g"),
    ("H15_ratevol_f20", "sd20_d1_DGS10", 20, "vol realizzata del 10 anni a 20g -> NQ 20g"),
]

if __name__ == "__main__":
    d, bars, daily = C.load()
    for tid, col, h, desc in TESTS:
        y, _ = C.fwd(d, h)
        st = C.ic_test(d[col], y)
        core.record(C.FAM, tid, "rank-IC " + desc + " (open RTH->open RTH, blocchi mensili)", "discovery", st,
                    signal=col, horizon=h, unit="rank-IC su ret %")
        print(f"{tid:22s} n={st['n']:5d} IC={st['ic']:+.3f} [{st['lo']:+.3f};{st['hi']:+.3f}] p={st['p_two']:.3f} anni+ {st['years_pos']}  {st['years']}")
