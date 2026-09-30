"""Eine fehlerhafte Displayseite zeigt „Anzeige-Fehler“, der Treiber und die G-Tasten laufen weiter."""
from harness import Sim
s = Sim("s13_fehler", macros={"profiles": [{"name": "P", "keys": {"M1": {"G1": {"text": "ok"}}}}]},
        settings={"start_page": 0, "notifications": {"enabled": False},
                  "layer_pages": {l: ["clock", "weather"] for l in ("M1", "M2", "M3")}})


def kaputt(self, profile, macros):
    raise ZeroDivisionError("Testfehler")


s.g.PAGE_RENDERERS["weather"] = kaputt
s.key(1.0, "RIGHT"); s.gkey(2.0, "G1"); s.key(3.0, "RIGHT"); s.gkey(4.0, "G1")
s.run(5)
s.save({"fehlerseite": 2.5})
s.finish(typed=s.typed(), pages=[[p, prof] for p, prof in s.page_seq()],
         log=[l for l in s.log_lines(r"^Anzeige-Fehler")])
