#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
四念処 — Satipaṭṭhāna Sutta (Majjhima Nikāya 10), as executable structure.
玄翁 / Gennō — companion plate to genno.html §三.

    The page stays thin. The weight is carried here.
    The v0 sketch on the page is not deleted. It is lapped beneath this plate (LAP_V0).

EPISTEMIC TAGS — every structural claim travels with its qualification.
    [TEXT mn10:x.y]  present in the sutta, at that SuttaCentral segment id
    [PE]             peyyāla: the sutta itself elides a repetition ("…pe…"). The full form is
                     retained elsewhere in the same text, so expanding it is recovery, not invention.
    [READING]        a choice this implementation makes that the text does not force
    [COMM]           from the Pāli commentarial tradition, not from the sutta
    [PARALLEL]       from comparative study of recensions (DN 22; Chinese Āgama parallels)
    [HELD]           unresolved on purpose; renderings kept side by side, not averaged

SOURCES — verifiable, resolvable.
    Pāli root:     SuttaCentral MN 10, Mahāsaṅgīti edition      https://suttacentral.net/mn10/pli/ms
    English:       Bhikkhu Sujato, "Mindfulness Meditation" (CC0) https://suttacentral.net/mn10/en/sujato
    Segments:      https://suttacentral.net/api/bilarasuttas/mn10/sujato
    Long recension DN 22 Mahāsatipaṭṭhāna Sutta                  https://suttacentral.net/dn22/en/sujato
    Parallels:     Anālayo, "Mindfulness-Based Interventions and the Four Satipaṭṭhānas"
                   https://www.buddhismuskunde.uni-hamburg.de/pdf/5-personen/analayo/mbissatipatthana.pdf

WHAT THE STRUCTURE IS (read this if you read nothing else)
    1. Ring.       The purpose statement (mn10:2.1) is repeated verbatim as the close (mn10:47.1).
                   The program ends where it began. That is an invariant, not a terminal state.
    2. Frame.      Four qualities accompany every observation: ātāpī, sampajāno, satimā,
                   vineyya loke abhijjhādomanassaṁ (mn10:3.2). Invariants, not goals.
    3. Lenses.     Four domains — kāya, vedanā, citta, dhammā — each observed "in itself"
                   (kāye kāyānupassī). 13 sections; the body's charnel section has 9 stages.
    4. Detector.   The core verb is pajānāti: the state is known under its own name.
                   'sarāgaṁ cittan'ti pajānāti — mind with greed, known as 'mind with greed'.
                   Quotation, not transformation. repr(), not eval(). No verdict is appended.
    5. Refrain.    After each of the 21 exercises, the same subroutine (mn10:5.1–5.3):
                   locus (internal / external / both) · dynamics (arising / vanishing / both) ·
                   bare existence, only to the measure of knowing · dwelling unsupported, grasping nothing.
    6. Lifecycles. In the fourth domain, items are tracked through time: present/absent → how the
                   unarisen arises → how the arisen is abandoned → how the abandoned does not recur
                   (hindrances, fetters), or → how the arisen is fulfilled by development (awakening
                   factors). Even here the verb stays pajānāti: one KNOWS how abandoning happens.
    7. Forecast.   After the exposition, outside it: seven years … seven days, one of two fruits
                   "may be expected" (pāṭikaṅkhaṁ). A forecast. It never feeds back into the loop.

NOT A SUBSTITUTE. Executing this file is not practice. It prints a trace of a structure.
これで全部ではない。写しに過ぎぬ。実物は座るところにある。
This is not the whole of it. It is only a copy. The real thing is where one sits.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable

# ═══════════════════════════════════════════════════════════════════════════════
# 0. HELD PLURAL                                                          [HELD]
#    Renderings that disagree are stored together. None is chosen as canonical.
# ═══════════════════════════════════════════════════════════════════════════════

HELD = {
    "ekāyana": {  # ekāyano ayaṁ, bhikkhave, maggo  [TEXT mn10:2.1]
        "literal": "one-going (eka + ayana)",
        "Sujato": "the path to convergence",
        "Anālayo": "the direct path",
        "Nyanasatta": "the only way",
    },
    "dīgha/rassa": {  # of the breath  [TEXT mn10:4.4–4.5]
        "literal": ("long", "short"),
        "Sujato": ("heavily", "lightly"),
    },
    "bahiddhā": {  # the "external" locus of the refrain  [TEXT mn10:5.1]
        "note": "The sutta does not say whose body/feeling/mind is 'external'. "
                "[COMM] reads it as another's. Left open here.",
    },
    "order": {
        "note": "[READING] The exposition presents the four domains in sequence, but gives no "
                "instruction that practice must run them in order, or all four per cycle. "
                "v0 swept all four each breath; this plate routes by what is arising. Both held.",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# 1. VERBS — the sutta's operations are distinct, and the distinction is structural
# ═══════════════════════════════════════════════════════════════════════════════


class Verb(Enum):
    VIHARATI = ("viharati", "dwells / meditates")              # continuous present; the loop itself
    PAJANATI = ("pajānāti", "knows / understands")             # read-only: the state under its own name
    SIKKHATI = ("sikkhati", "trains")                          # write: shapes the next breath (4.6–4.7 only)
    SAMPAJANAKARI = ("sampajānakārī hoti", "acts aware")       # a manner wrapped around action (8.1 only)
    PACCAVEKKHATI = ("paccavekkhati", "examines / reviews")    # traversal of parts (10, 12)
    UPASAMHARATI = ("upasaṁharati", "compares")                # applies another body's case to one's own (14–30)
    ELIDED = ("(—)", "no verb in the Pāli")                    # aggregates (38.3–38.8): the verb is absent
    AVOCA = ("avoca", "said")                                  # the frame narration: statements, not operations


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TRACE — a note is a record, not a judgment
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Note:
    seg: str
    verb: Verb
    pali: str
    english: str
    tag: str = "TEXT"


TRACE: list[Note] = []


def note(seg: str, verb: Verb, pali: str, english: str, tag: str = "TEXT") -> Note:
    # 判断せず、ただ記す / not a judgment — a record
    n = Note(seg, verb, pali, english, tag)
    TRACE.append(n)
    print(f"  [{tag:<7}] {seg:<16} {verb.value[0]:<18} {pali}\n{'':<46}— {english}")
    return n


def know(seg: str, state_pali: str, state_en: str) -> Note:
    """[TEXT] Form: <state> '<state>'ti pajānāti.
    [READING] The label is the state's own name. Nothing is added: no score, no correction,
    no branch on whether the state is wholesome. The detector is identity under quotation."""
    return note(seg, Verb.PAJANATI, f"'{state_pali}'ti pajānāti", f"knows: '{state_en}'")


def know_how(seg: str, process_pali: str, process_en: str) -> Note:
    """[TEXT mn10:36.4, 40.3, 42.3] Form: yathā ca … hoti, tañca pajānāti — 'and that too one knows'.
    Not a quotation of a state but knowledge of a process: how something comes to be, or goes."""
    return note(seg, Verb.PAJANATI, f"{process_pali}, tañca pajānāti", f"knows {process_en}")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. THE PHENOMENON — what arrives, and where, and in which phase
# ═══════════════════════════════════════════════════════════════════════════════


class Locus(Enum):  # [TEXT mn10:5.1]
    INTERNAL = ("ajjhattaṁ", "internally")
    EXTERNAL = ("bahiddhā", "externally")
    BOTH = ("ajjhattabahiddhā", "internally and externally")


class Phase(Enum):  # [TEXT mn10:5.2]
    ARISING = ("samudayadhammānupassī", "the liability to originate")
    VANISHING = ("vayadhammānupassī", "the liability to vanish")
    BOTH = ("samudayavayadhammānupassī", "the liability to originate and vanish")


@dataclass
class Phenomenon:
    domain: str                 # "kāya" | "vedanā" | "citta" | "dhammā"
    kind: str                   # section key in SECTIONS
    value: object               # the state itself, in the section's own vocabulary
    locus: Locus = Locus.INTERNAL
    phase: Phase = Phase.BOTH


@dataclass
class Practitioner:
    """The frame.  [TEXT mn10:3.2–3.5]
    ātāpī sampajāno satimā, vineyya loke abhijjhādomanassaṁ
    keen, aware, and mindful, rid of covetousness and displeasure for the world."""
    atapi: bool = True        # ātāpī — keen, ardent
    sampajano: bool = True    # sampajāno — aware, clearly comprehending
    satima: bool = True       # satimā — mindful
    vineyya: bool = True      # vineyya loke abhijjhādomanassaṁ — having put away covetousness & displeasure
    upadisesa: bool = True    # sati vā upādisese — "if there is some substrate left"  [TEXT mn10:46.2]

    def frame_holds(self) -> bool:
        # [READING] `vineyya` is an absolutive standing beside the other three qualities:
        # it accompanies the observing; it is not a condition the loop waits to reach.
        return self.atapi and self.sampajano and self.satima and self.vineyya


# ═══════════════════════════════════════════════════════════════════════════════
# 4. THE REFRAIN — one subroutine, called 21 times            [TEXT mn10:5.1–5.4]
# ═══════════════════════════════════════════════════════════════════════════════

DOMAIN = {
    #          compound                  'atthi __'ti  English       verb
    "kāya":   ("kāye kāyānupassī",       "kāyo",   "the body",   "exists"),
    "vedanā": ("vedanāsu vedanānupassī", "vedanā", "feelings",   "exist"),
    "citta":  ("citte cittānupassī",     "cittaṁ", "the mind",   "exists"),
    "dhammā": ("dhammesu dhammānupassī", "dhammā", "principles", "exist"),
}


def refrain(ph: Phenomenon, seg: str, closing: str, abbreviated: bool) -> None:
    """[TEXT mn10:5.1–5.4, 33, 35, 37, 39, 41, 43, 45, 31]
    [PE] From mn10:9.1 onward the sutta writes only "internally …". The full form, retained at
         mn10:5.1–5.3 and repeated in full at 31, 33, 35, 37…, is the recipe that recovers it.
    [READING] 'vā … vā … vā' is disjunctive: internally OR externally OR both. The subroutine
         observes whichever locus and phase the phenomenon actually presents. No forced triple sweep."""
    tag = "PE" if abbreviated else "TEXT"
    compound, exists, en, is_are = DOMAIN[ph.domain]
    s1, s2, s3 = (f"{seg}.1",) * 3 if abbreviated else (f"{seg}.1", f"{seg}.2", f"{seg}.3")
    note(s1, Verb.VIHARATI, f"iti {ph.locus.value[0]} vā {compound} viharati",
         f"observes an aspect of {en} {ph.locus.value[1]}", tag)
    note(s2, Verb.VIHARATI, f"{ph.phase.value[0]} vā viharati",
         f"observes, with respect to {en}, {ph.phase.value[1]}", tag)
    note(s3, Verb.VIHARATI, f"'atthi {exists}'ti vā panassa sati paccupaṭṭhitā hoti",
         f"or mindfulness is established that {en} {is_are}", tag)
    note(s3, Verb.VIHARATI, "yāvadeva ñāṇamattāya paṭissatimattāya",
         "just to the extent necessary for knowledge and mindfulness", tag)
    note(s3, Verb.VIHARATI, "anissito ca viharati, na ca kiñci loke upādiyati",
         "dwells independent, not grasping at anything in the world", tag)
    note(closing, Verb.VIHARATI, f"evampi kho, bhikkhave, bhikkhu {compound} viharati",
         f"that too is how one meditates observing an aspect of {en}", tag)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. 身念処  KĀYĀNUPASSANĀ — the body in the body            [TEXT mn10:4–31]
# ═══════════════════════════════════════════════════════════════════════════════

# 5.1 Ānāpānasati — mindfulness of breathing                 [TEXT mn10:4.1–4.11]

SETTING = [  # [TEXT mn10:4.2] — a precondition, stated once, not per breath
    ("araññagato vā rukkhamūlagato vā suññāgāragato vā",
     "gone to a wilderness, or to the root of a tree, or to an empty hut"),
    ("nisīdati pallaṅkaṁ ābhujitvā ujuṁ kāyaṁ paṇidhāya", "sits cross-legged, body set straight"),
    ("parimukhaṁ satiṁ upaṭṭhapetvā", "brings mindfulness to the present"),
    ("so satova assasati, satova passasati", "just mindful, breathes in; mindful, breathes out"),
]


def anapanasati(p: Practitioner, ph: Phenomenon) -> None:
    direction, length = ph.value            # ("in" | "out", "dīgha" | "rassa")
    verb_pali = "assasāmī" if direction == "in" else "passasāmī"
    verb_en = "breathing in" if direction == "in" else "breathing out"
    long_en = {"dīgha": "long", "rassa": "short"}[length]
    # Tetrad steps 1–2: detection. The breath is not lengthened or shortened; it is known.
    know("mn10:4.4–4.5", f"{length}ṁ {verb_pali}", f"I'm {verb_en} {long_en}")  # [HELD] Sujato: heavily / lightly
    # Tetrad steps 3–4: the verb changes. pajānāti → sikkhati. Read becomes write.
    # [READING] This is the only place in MN 10 where the practitioner is told to shape, not only see.
    fut = "assasissāmī" if direction == "in" else "passasissāmī"
    note("mn10:4.6", Verb.SIKKHATI, f"'sabbakāyapaṭisaṁvedī {fut}'ti sikkhati",
         f"trains: 'I'll breathe {direction} experiencing the whole body'")
    note("mn10:4.7", Verb.SIKKHATI, f"'passambhayaṁ kāyasaṅkhāraṁ {fut}'ti sikkhati",
         f"trains: 'I'll breathe {direction} stilling the physical process'")


SIMILE_LATHE = (  # [TEXT mn10:4.8–4.11]
    "dakkho bhamakāro vā bhamakārantevāsī vā dīghaṁ vā añchanto 'dīghaṁ añchāmī'ti pajānāti",
    "a deft lathe-turner, drawing a long pull, knows 'I'm drawing a long pull'",
    "[READING] the skilled worker's knowing does not interrupt the work",
)

# 5.2 Iriyāpatha — the postures                              [TEXT mn10:6.1–6.2]

POSTURES = {
    "walking":  ("gacchanto", "gacchāmi"),
    "standing": ("ṭhito", "ṭhitomhi"),
    "sitting":  ("nisinno", "nisinnomhi"),
    "lying":    ("sayāno", "sayānomhi"),
}


def iriyapatha(p: Practitioner, ph: Phenomenon) -> None:
    posture = ph.value
    if posture in POSTURES:
        _, first_person = POSTURES[posture]
        know("mn10:6.1", first_person, f"I am {posture}")
    else:
        # [TEXT mn10:6.2] yathā yathā vā panassa kāyo paṇihito hoti, tathā tathā naṁ pajānāti
        # The sutta supplies its own wildcard branch. The enumeration is not a closed type.
        note("mn10:6.2", Verb.PAJANATI,
             "yathā yathā vā panassa kāyo paṇihito hoti, tathā tathā naṁ pajānāti",
             f"whatever posture their body is in, they know it  (here: {posture})")


# 5.3 Sampajañña — situational awareness                     [TEXT mn10:8.1]

ACTIVITIES = {
    "going_out_coming_back": ("abhikkante paṭikkante", "going out and coming back"),
    "looking":               ("ālokite vilokite", "looking ahead and aside"),
    "bending_extending":     ("samiñjite pasārite", "bending and extending the limbs"),
    "robes_bowl":            ("saṅghāṭipattacīvaradhāraṇe", "bearing the outer robe, bowl and robes"),
    "eating":                ("asite pīte khāyite sāyite", "eating, drinking, chewing, and tasting"),
    "excreting":             ("uccārapassāvakamme", "urinating and defecating"),
    "all_else":              ("gate ṭhite nisinne sutte jāgarite bhāsite tuṇhībhāve",
                              "walking, standing, sitting, sleeping, waking, speaking, keeping silent"),
}


def sampajanakari(activity: str) -> Callable[[Callable[..., object]], Callable[..., object]]:
    """[READING] The only body exercise whose verb is a manner of doing rather than a kind of
    seeing. So it is a decorator: it does not observe a separate object; it wraps the act."""
    pali, en = ACTIVITIES[activity]

    def wrap(act: Callable[..., object]) -> Callable[..., object]:
        def inner(*args: object, **kwargs: object) -> object:
            note("mn10:8.1", Verb.SAMPAJANAKARI, f"{pali} sampajānakārī hoti",
                 f"acts with situational awareness when {en}")
            return act(*args, **kwargs)
        return inner
    return wrap


def sampajanna(p: Practitioner, ph: Phenomenon) -> None:
    @sampajanakari(ph.value)
    def act() -> None:
        pass  # the action itself belongs to the world, not to this file
    act()


# 5.4 Paṭikūlamanasikāra — the thirty-one parts              [TEXT mn10:10.1–10.5]

ANATOMY = [  # MN 10 lists 31. [PARALLEL] later lists add matthaluṅga (brain) → 32.
    ("kesā", "head hair"), ("lomā", "body hair"), ("nakhā", "nails"), ("dantā", "teeth"),
    ("taco", "skin"), ("maṁsaṁ", "flesh"), ("nahāru", "sinews"), ("aṭṭhī", "bones"),
    ("aṭṭhimiñjaṁ", "bone marrow"), ("vakkaṁ", "kidneys"), ("hadayaṁ", "heart"),
    ("yakanaṁ", "liver"), ("kilomakaṁ", "diaphragm"), ("pihakaṁ", "spleen"),
    ("papphāsaṁ", "lungs"), ("antaṁ", "intestines"), ("antaguṇaṁ", "mesentery"),
    ("udariyaṁ", "undigested food"), ("karīsaṁ", "feces"), ("pittaṁ", "bile"),
    ("semhaṁ", "phlegm"), ("pubbo", "pus"), ("lohitaṁ", "blood"), ("sedo", "sweat"),
    ("medo", "fat"), ("assu", "tears"), ("vasā", "grease"), ("kheḷo", "saliva"),
    ("siṅghāṇikā", "snot"), ("lasikā", "synovial fluid"), ("muttaṁ", "urine"),
]
GRAINS = [("sāli", "fine rice"), ("vīhi", "wheat [Sujato]"), ("mugga", "mung beans"),
          ("māsa", "peas"), ("tila", "sesame"), ("taṇḍula", "ordinary rice")]


def patikula(p: Practitioner, ph: Phenomenon) -> None:
    # [TEXT mn10:10.1] uddhaṁ pādatalā adho kesamatthakā — up from the soles, down from the hair tips.
    # [READING] traversal in both directions over a bounded container (tacapariyanta: wrapped in skin).
    note("mn10:10.1", Verb.PACCAVEKKHATI,
         "imameva kāyaṁ uddhaṁ pādatalā adho kesamatthakā tacapariyantaṁ … paccavekkhati",
         "examines this very body, up from the soles, down from the tips of the hairs, wrapped in skin")
    order = ANATOMY if ph.value != "descending" else list(reversed(ANATOMY))
    note("mn10:10.2", Verb.PACCAVEKKHATI, " ".join(pali for pali, _ in order),
         ", ".join(en for _, en in order))
    # [TEXT mn10:10.3] The bag simile. A person with good eyes opens a two-mouthed bag and sorts grain.
    # [READING] The operation is classification. The sorter does not recoil from the grain.
    note("mn10:10.3", Verb.PACCAVEKKHATI, "mutoḷī ubhatomukhā … cakkhumā puriso muñcitvā paccavekkheyya",
         "as one with clear eyes would open a bag and sort: " + ", ".join(en for _, en in GRAINS))


# 5.5 Dhātumanasikāra — the four elements                    [TEXT mn10:12.1–12.5]

ELEMENTS = [("pathavīdhātu", "earth element"), ("āpodhātu", "water element"),
            ("tejodhātu", "fire element"), ("vāyodhātu", "air element")]


def dhatu(p: Practitioner, ph: Phenomenon) -> None:
    # [TEXT mn10:12.1] yathāṭhitaṁ yathāpaṇihitaṁ — whatever its placement or posture.
    # [READING] Posture-invariant: this analysis takes no input from 5.2.
    note("mn10:12.1", Verb.PACCAVEKKHATI, "imameva kāyaṁ yathāṭhitaṁ yathāpaṇihitaṁ dhātuso paccavekkhati",
         "examines this very body, whatever its placement or posture, by elements")
    for pali, en in ELEMENTS:
        note("mn10:12.2", Verb.PACCAVEKKHATI, f"atthi imasmiṁ kāye {pali}", f"in this body there is the {en}")
    # [TEXT mn10:12.3] The butcher at the crossroads, the cow cut into portions.
    # [COMM] Once cut, the butcher no longer holds the notion 'cow' — only portions. Not in the sutta.
    note("mn10:12.3", Verb.PACCAVEKKHATI, "dakkho goghātako … catumahāpathe bilaso vibhajitvā nisinno assa",
         "as a deft butcher would sit at the crossroads with the meat cut into portions")


# 5.6 Navasivathikā — the nine charnel-ground stages         [TEXT mn10:14–31]

CHARNEL = [
    # (segment, pali, english, refrain_segment, refrain_abbreviated)
    ("mn10:14.1", "ekāhamataṁ vā dvīhamataṁ vā tīhamataṁ vā uddhumātakaṁ vinīlakaṁ vipubbakajātaṁ",
     "dead one, two, or three days — bloated, livid, festering", "mn10:15", True),
    ("mn10:16.1", "kākehi … kulalehi … gijjhehi … kaṅkehi … sunakhehi … byagghehi … dīpīhi … "
                  "siṅgālehi … vividhehi vā pāṇakajātehi khajjamānaṁ",
     "devoured by crows, hawks, vultures, herons, hounds, tigers, leopards, jackals, little creatures",
     "mn10:17", True),
    ("mn10:18–23", "aṭṭhikasaṅkhalikaṁ samaṁsalohitaṁ nhārusambandhaṁ",
     "a skeleton with flesh and blood, held together by sinews", "mn10:18–23", True),
    ("mn10:18–23", "aṭṭhikasaṅkhalikaṁ nimmaṁsalohitamakkhitaṁ nhārusambandhaṁ",
     "a skeleton without flesh, smeared with blood, held together by sinews", "mn10:18–23", True),
    ("mn10:18–23", "aṭṭhikasaṅkhalikaṁ apagatamaṁsalohitaṁ nhārusambandhaṁ",
     "a skeleton rid of flesh and blood, held together by sinews", "mn10:18–23", True),
    ("mn10:24.1", "aṭṭhikāni apagatasambandhāni disā vidisā vikkhittāni",
     "bones rid of sinews, scattered in every direction: hand, foot, ankle, shin, thigh, hip, "
     "rib, back, arm, neck, jaw, tooth, skull", "mn10:25", True),
    ("mn10:26–28", "aṭṭhikāni setāni saṅkhavaṇṇapaṭibhāgāni",
     "white bones, the color of shells", "mn10:26–28", True),
    ("mn10:29.1", "aṭṭhikāni puñjakitāni terovassikāni",
     "decrepit bones, heaped in a pile, more than a year old", "mn10:29", True),
    ("mn10:30.1", "aṭṭhikāni pūtīni cuṇṇakajātāni",
     "bones rotted and crumbled to powder", "mn10:31", False),
]


def sivathika(p: Practitioner, ph: Phenomenon) -> tuple[str, bool]:
    stage = int(ph.value)                       # 1..9
    seg, pali, en, rseg, abbrev = CHARNEL[stage - 1]
    note(seg, Verb.UPASAMHARATI, f"sivathikāya chaḍḍitaṁ … {pali}", f"sees a corpse in a charnel ground: {en}",
         "PE" if abbrev and stage not in (1, 2) else "TEXT")
    # [TEXT mn10:14.2–14.3, 30.2–30.3] The comparison. Three predicates, no exemption clause.
    # [READING] A universal statement applied reflexively: whatever holds of that body holds of this one.
    note(seg, Verb.UPASAMHARATI, "so imameva kāyaṁ upasaṁharati: 'ayampi kho kāyo evaṁdhammo "
         "evaṁbhāvī evaṁanatīto'ti",
         "compares it with their own body: 'this body is also of that same nature, "
         "that same kind, and cannot go beyond that'")
    return rseg, abbrev


# ═══════════════════════════════════════════════════════════════════════════════
# 6. 受念処  VEDANĀNUPASSANĀ — feelings in feelings           [TEXT mn10:32–33]
# ═══════════════════════════════════════════════════════════════════════════════

VALENCE = {"pleasant": "sukhaṁ", "painful": "dukkhaṁ", "neutral": "adukkhamasukhaṁ"}
AMISA = {None: ("", ""), "of_the_flesh": ("sāmisaṁ ", "of the flesh "),
         "not_of_the_flesh": ("nirāmisaṁ ", "not of the flesh ")}
# State space: 3 valences × {unqualified, sāmisa, nirāmisa} = 9.  [TEXT mn10:32.2–32.10]


def vedana(p: Practitioner, ph: Phenomenon) -> None:
    valence, amisa = ph.value
    if valence not in VALENCE or amisa not in AMISA:
        unmatched(ph, "vedanā state outside the sutta's 9-case space")
        return
    a_pali, a_en = AMISA[amisa]
    en = f"{valence} feeling {a_en}".replace("  ", " ").strip()
    know("mn10:32", f"{a_pali}{VALENCE[valence]} vedanaṁ vedayāmi", f"I feel a {en}")


# ═══════════════════════════════════════════════════════════════════════════════
# 7. 心念処  CITTĀNUPASSANĀ — mind in mind                   [TEXT mn10:34–35]
# ═══════════════════════════════════════════════════════════════════════════════

MIND_PAIRS = [  # eight pairs, sixteen states, in the sutta's order
    (("sarāgaṁ", "mind with greed"), ("vītarāgaṁ", "mind without greed")),
    (("sadosaṁ", "mind with hate"), ("vītadosaṁ", "mind without hate")),
    (("samohaṁ", "mind with delusion"), ("vītamohaṁ", "mind without delusion")),
    (("saṅkhittaṁ", "constricted mind"), ("vikkhittaṁ", "scattered mind")),
    (("mahaggataṁ", "expansive mind"), ("amahaggataṁ", "unexpansive mind")),
    (("sa-uttaraṁ", "mind that is not supreme"), ("anuttaraṁ", "mind that is supreme")),
    (("samāhitaṁ", "mind immersed in samādhi"), ("asamāhitaṁ", "mind not immersed in samādhi")),
    (("vimuttaṁ", "freed mind"), ("avimuttaṁ", "unfreed mind")),
]
MIND_STATES = {pali: (i, en) for i, pair in enumerate(MIND_PAIRS) for pali, en in pair}


def citta(p: Practitioner, ph: Phenomenon) -> None:
    state = ph.value
    if state not in MIND_STATES:
        unmatched(ph, "citta state outside the sutta's sixteen")
        return
    i, en = MIND_STATES[state]
    # [READING] No preferred pole. 'Mind with greed' and 'freed mind' pass through the same line.
    know(f"mn10:34.{2 + 2 * i}–{3 + 2 * i}", f"{state} cittaṁ", en)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. 法念処  DHAMMĀNUPASSANĀ — principles in principles        [TEXT mn10:36–45]
# ═══════════════════════════════════════════════════════════════════════════════

# 8.0 Lifecycle — the shared state machine of hindrances, fetters, awakening factors.
#     Two terminals, mirror images:
#       ABANDON : present? → unarisen arises → arisen is abandoned → abandoned does not recur
#       FULFIL  : present? → unarisen arises → arisen is fulfilled by development
#     [READING] Every transition is still preceded by 'tañca pajānāti' — "and that too one knows".
#     The file never calls release(). It records knowing how release comes about.


def lifecycle(seg: str, nom: str, gen: str, en: str, event: str, terminal: str) -> None:
    if event == "present":
        know(seg, f"atthi me ajjhattaṁ {nom}", f"{en} is present in me")
    elif event == "absent":
        know(seg, f"natthi me ajjhattaṁ {nom}", f"{en} is not present in me")
    elif event == "arising":
        know_how(seg, f"yathā ca anuppannassa {gen} uppādo hoti", f"how {en} comes to be, where it had not arisen")
    elif event == "abandoning" and terminal == "abandon":
        know_how(seg, f"yathā ca uppannassa {gen} pahānaṁ hoti", f"how {en}, once arisen, is abandoned")
    elif event == "non-recurrence" and terminal == "abandon":
        know_how(seg, f"yathā ca pahīnassa {gen} āyatiṁ anuppādo hoti",
                 f"how {en}, once abandoned, does not come to be again in the future")
    elif event == "fulfilment" and terminal == "fulfil":
        know_how(seg, f"yathā ca uppannassa {gen} bhāvanāya pāripūrī hoti",
                 f"how {en}, once arisen, is fulfilled by development")
    else:
        # e.g. 'abandoning' asked of an awakening factor. The sutta has no such transition.
        note(seg, Verb.PAJANATI, f"({nom}: {event})", "transition not in the sutta; not executed", "READING")


# 8.1 Nīvaraṇa — the five hindrances                         [TEXT mn10:36.1–36.8]

HINDRANCES = {  # key: (nominative, genitive, Sujato, literal)
    "kāmacchanda":      ("kāmacchando", "kāmacchandassa", "desire", "sensual desire"),
    "byāpāda":          ("byāpādo", "byāpādassa", "ill-will", "ill-will"),
    "thinamiddha":      ("thinamiddhaṁ", "thinamiddhassa", "sluggishness", "dullness and drowsiness"),
    "uddhaccakukkucca": ("uddhaccakukkuccaṁ", "uddhaccakukkuccassa", "restlessness", "restlessness and remorse"),
    "vicikicchā":       ("vicikicchā", "vicikicchāya", "doubt", "doubt"),
}


def nivarana(p: Practitioner, ph: Phenomenon) -> None:
    key, event = ph.value
    nom, gen, en, _ = HINDRANCES[key]
    lifecycle("mn10:36.4–36.8", nom, gen, en, event, terminal="abandon")


# 8.2 Upādānakkhandha — the five aggregates                  [TEXT mn10:38.1–38.8]

AGGREGATES = {  # key: (nominative, genitive, Sujato)
    "rūpa":      ("rūpaṁ", "rūpassa", "form"),
    "vedanā":    ("vedanā", "vedanāya", "feeling"),
    "saññā":     ("saññā", "saññāya", "perception"),
    "saṅkhārā":  ("saṅkhārā", "saṅkhārānaṁ", "volition"),
    "viññāṇa":   ("viññāṇaṁ", "viññāṇassa", "consciousness"),
}


def khandha(p: Practitioner, ph: Phenomenon) -> None:
    key, aspect = ph.value  # aspect ∈ {"itself", "origin", "ending"}
    nom, gen, en = AGGREGATES[key]
    pali = {"itself": f"iti {nom}", "origin": f"iti {gen} samudayo", "ending": f"iti {gen} atthaṅgamo"}[aspect]
    eng = {"itself": f"that is {en}", "origin": f"that is the origin of {en}",
           "ending": f"that is the ending of {en}"}[aspect]
    # [TEXT mn10:38.3] "Idha, bhikkhave, bhikkhu: 'iti rūpaṁ …'" — the Pāli gives no verb here.
    # [HELD] Sujato supplies 'understands' inside the quotation marks. The elision is the text's own;
    # it is recorded as Verb.ELIDED rather than silently filled with pajānāti.
    # [READING] A triple per aggregate: the thing, where it comes from, where it goes. No fourth slot
    # for what it 'really' is. [PARALLEL] Absent from MĀ 98 and EĀ 12.1 (Anālayo, Table 2).
    note("mn10:38.4–38.8", Verb.ELIDED, pali, f"[understands:] {eng}")


# 8.3 Āyatana — six interior and exterior sense bases        [TEXT mn10:40.1–40.8]

SENSE_BASES = {  # key: (interior, exterior, Sujato interior, Sujato exterior)
    "eye":    ("cakkhu", "rūpe", "the eye", "forms"),
    "ear":    ("sota", "sadde", "the ear", "sounds"),
    "nose":   ("ghāna", "gandhe", "the nose", "smells"),
    "tongue": ("jihvā", "rase", "the tongue", "tastes"),
    "body":   ("kāya", "phoṭṭhabbe", "the body", "tangibles"),
    "mind":   ("mana", "dhamme", "the mind", "principles"),
}


def ayatana(p: Practitioner, ph: Phenomenon) -> None:
    key, event = ph.value
    inner, outer, inner_en, outer_en = SENSE_BASES[key]
    if event == "contact":
        # [TEXT] cakkhuñca pajānāti, rūpe ca pajānāti — each end known; no quotation form here.
        note("mn10:40.3–40.8", Verb.PAJANATI, f"{inner}ñca pajānāti, {outer} ca pajānāti",
             f"understands {inner_en} and {outer_en}")
        # [TEXT] yañca tadubhayaṁ paṭicca uppajjati saṁyojanaṁ tañca pajānāti
        # [READING] The fetter is an edge, not a node: it arises dependent on both ends of the pair.
        know_how("mn10:40.3–40.8", "yañca tadubhayaṁ paṭicca uppajjati saṁyojanaṁ",
                 "the bond that arises dependent on both")
    else:
        lifecycle("mn10:40.3–40.8", "saṁyojanaṁ", "saṁyojanassa", f"the bond between {inner_en} and {outer_en}",
                  event, terminal="abandon")


# 8.4 Bojjhaṅga — the seven awakening factors                [TEXT mn10:42.1–42.9]

AWAKENING_FACTORS = {  # key: (nominative, genitive, Sujato)
    "sati":         ("satisambojjhaṅgo", "satisambojjhaṅgassa", "the mindfulness awakening factor"),
    "dhammavicaya": ("dhammavicayasambojjhaṅgo", "dhammavicayasambojjhaṅgassa",
                     "the investigation of principles awakening factor"),
    "vīriya":       ("vīriyasambojjhaṅgo", "vīriyasambojjhaṅgassa", "the energy awakening factor"),
    "pīti":         ("pītisambojjhaṅgo", "pītisambojjhaṅgassa", "the joy awakening factor"),
    "passaddhi":    ("passaddhisambojjhaṅgo", "passaddhisambojjhaṅgassa", "the tranquility awakening factor"),
    "samādhi":      ("samādhisambojjhaṅgo", "samādhisambojjhaṅgassa", "the immersion awakening factor"),
    "upekkhā":      ("upekkhāsambojjhaṅgo", "upekkhāsambojjhaṅgassa", "the equanimity awakening factor"),
}


def bojjhanga(p: Practitioner, ph: Phenomenon) -> None:
    key, event = ph.value
    nom, gen, en = AWAKENING_FACTORS[key]
    # [PARALLEL] The only fourth-domain exercise shared by MN 10, MĀ 98, and EĀ 12.1 (Anālayo, Table 2).
    lifecycle("mn10:42.3–42.9", nom, gen, en, event, terminal="fulfil")


# 8.5 Ariyasacca — the four noble truths                     [TEXT mn10:44.1–44.3]

TRUTHS = {
    "dukkha":   ("idaṁ dukkhaṁ", "this is suffering"),
    "samudaya": ("ayaṁ dukkhasamudayo", "this is the origin of suffering"),
    "nirodha":  ("ayaṁ dukkhanirodho", "this is the ending of suffering"),
    "magga":    ("ayaṁ dukkhanirodhagāminī paṭipadā", "this is the path leading to the ending of suffering"),
}

# [PARALLEL][HELD] DN 22 expands each truth at length (definitions of suffering, craving at each
# sense base, the eightfold path). Not implemented here: MN 10 is the text in hand.
# This is a marked absence with recovery evidence — the expansion is retained, at the DN 22 URL above.
DN22_TRUTHS_EXPANSION = NotImplemented


def sacca(p: Practitioner, ph: Phenomenon) -> None:
    pali, en = TRUTHS[ph.value]
    note("mn10:44.3", Verb.PAJANATI, f"'{pali}'ti yathābhūtaṁ pajānāti", f"understands as it actually is: '{en}'")


# ═══════════════════════════════════════════════════════════════════════════════
# 9. THE UNMATCHED FRACTION                                             [READING]
#    The sutta's state spaces are given. Input outside them is not coerced into the nearest
#    category and not discarded. It is logged as seen-but-unclassified, and the loop goes on.
# ═══════════════════════════════════════════════════════════════════════════════

UNMATCHED: list[Phenomenon] = []


def unmatched(ph: Phenomenon, why: str) -> None:
    UNMATCHED.append(ph)
    note("—", Verb.PAJANATI, f"({ph.domain}/{ph.kind}: {ph.value!r})", f"held as unmatched: {why}", "READING")


# ═══════════════════════════════════════════════════════════════════════════════
# 10. SECTION TABLE — 13 sections, 21 refrain calls
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Section:
    domain: str
    number: str
    pali: str
    english: str
    run: Callable[[Practitioner, Phenomenon], object]
    refrain_seg: str
    closing_seg: str
    abbreviated: bool
    parallels: str = "not checked"


SECTIONS: dict[str, Section] = {
    "breath":    Section("kāya", "1.1", "ānāpānasati", "Mindfulness of Breathing", anapanasati,
                         "mn10:5", "mn10:5.4", False, "absent from EĀ 12.1"),
    "posture":   Section("kāya", "1.2", "iriyāpatha", "The Postures", iriyapatha,
                         "mn10:7", "mn10:7.4", False, "absent from EĀ 12.1"),
    "activity":  Section("kāya", "1.3", "sampajañña", "Situational Awareness", sampajanna,
                         "mn10:9", "mn10:9.2", True, "absent from EĀ 12.1"),
    "anatomy":   Section("kāya", "1.4", "paṭikūlamanasikāra", "Focusing on the Repulsive", patikula,
                         "mn10:11", "mn10:11.2", True, "shared by MN 10, MĀ 98, EĀ 12.1"),
    "elements":  Section("kāya", "1.5", "dhātumanasikāra", "Focusing on the Elements", dhatu,
                         "mn10:13", "mn10:13.2", True, "shared by MN 10, MĀ 98, EĀ 12.1"),
    "charnel":   Section("kāya", "1.6", "navasivathikā", "The Charnel Ground Contemplations", sivathika,
                         "(per stage)", "(per stage)", True, "shared by MN 10, MĀ 98, EĀ 12.1"),
    "feeling":   Section("vedanā", "2", "vedanānupassanā", "Observing the Feelings", vedana,
                         "mn10:33", "mn10:33.4", False),
    "mind":      Section("citta", "3", "cittānupassanā", "Observing the Mind", citta,
                         "mn10:35", "mn10:35.4", False),
    "hindrance": Section("dhammā", "4.1", "nīvaraṇa", "The Hindrances", nivarana,
                         "mn10:37", "mn10:37.4", False, "MN 10, MĀ 98; absent from EĀ 12.1"),
    "aggregate": Section("dhammā", "4.2", "upādānakkhandha", "The Aggregates", khandha,
                         "mn10:39", "mn10:39.4", False, "absent from MĀ 98 and EĀ 12.1"),
    "sensebase": Section("dhammā", "4.3", "āyatana", "The Sense Bases", ayatana,
                         "mn10:41", "mn10:41.4", False, "MN 10, MĀ 98; absent from EĀ 12.1"),
    "factor":    Section("dhammā", "4.4", "bojjhaṅga", "The Awakening Factors", bojjhanga,
                         "mn10:43", "mn10:43.4", False, "shared by MN 10, MĀ 98, EĀ 12.1"),
    "truth":     Section("dhammā", "4.5", "ariyasacca", "The Noble Truths", sacca,
                         "mn10:45", "mn10:45.4", False, "absent from MĀ 98 and EĀ 12.1"),
}

# Counted from the text: 5 non-charnel body sections + 9 charnel stages + 1 + 1 + 5 = 21.
REFRAIN_COUNT = sum(1 for s in SECTIONS.values() if s.run is not sivathika) + len(CHARNEL)
assert REFRAIN_COUNT == 21
assert len(ANATOMY) == 31
assert len(MIND_STATES) == 16
assert len(VALENCE) * len(AMISA) == 9


# ═══════════════════════════════════════════════════════════════════════════════
# 11. UDDESA, FORECAST, RING
# ═══════════════════════════════════════════════════════════════════════════════

PURPOSE = (  # [TEXT mn10:2.1] and, verbatim, [TEXT mn10:47.1]
    ("sattānaṁ visuddhiyā", "to purify sentient beings"),
    ("sokaparidevānaṁ samatikkamāya", "to get past sorrow and crying"),
    ("dukkhadomanassānaṁ atthaṅgamāya", "to make an end of pain and sadness"),
    ("ñāyassa adhigamāya", "to discover the system"),
    ("nibbānassa sacchikiriyāya", "to realize extinguishment"),
)
CLOSING = PURPOSE  # the ring: the last statement is the first statement


def uddesa(p: Practitioner) -> None:
    print("\nNIDĀNA  mn10:1.1–1.6 — evaṁ me sutaṁ. Kurūsu … Kammāsadhammaṁ nāma kurūnaṁ nigamo.")
    note("mn10:2.1", Verb.AVOCA, "ekāyano ayaṁ, bhikkhave, maggo … yadidaṁ cattāro satipaṭṭhānā",
         f"the four kinds of mindfulness meditation are [HELD: {' | '.join(v for k, v in HELD['ekāyana'].items())}]")
    for pali, en in PURPOSE:
        note("mn10:2.1", Verb.AVOCA, pali, en)
    for domain, (compound, _, en, _v) in DOMAIN.items():
        note("mn10:3.2–3.5", Verb.VIHARATI,
             f"{compound} viharati ātāpī sampajāno satimā, vineyya loke abhijjhādomanassaṁ",
             f"meditates observing an aspect of {en} — keen, aware, mindful, "
             f"rid of covetousness and displeasure for the world")


SCHEDULE = [  # [TEXT mn10:46.1–46.23] a descending series; most steps are [PE] 'tiṭṭhantu' — let alone
    ("satta vassāni", "seven years"), ("cha vassāni", "six years"), ("pañca vassāni", "five years"),
    ("cattāri vassāni", "four years"), ("tīṇi vassāni", "three years"), ("dve vassāni", "two years"),
    ("ekaṁ vassaṁ", "one year"),
    ("satta māsāni", "seven months"), ("cha māsāni", "six months"), ("pañca māsāni", "five months"),
    ("cattāri māsāni", "four months"), ("tīṇi māsāni", "three months"), ("dve māsāni", "two months"),
    ("ekaṁ māsaṁ", "one month"), ("aḍḍhamāsaṁ", "half a month"),
    ("sattāhaṁ", "seven days"),
]


def expected_fruit(p: Practitioner) -> tuple[str, str]:
    """[TEXT mn10:46.2] dvinnaṁ phalānaṁ aññataraṁ phalaṁ pāṭikaṅkhaṁ:
    diṭṭheva dhamme aññā, sati vā upādisese anāgāmitā.
    [READING] Pure function. A forecast ('may be expected'), stated after the exposition and outside
    it. It is never called from inside dwell(); it cannot end the dwelling."""
    if p.upadisesa:
        return ("anāgāmitā", "non-return (some substrate left)")
    return ("diṭṭheva dhamme aññā", "final knowledge in this very life")


def forecast(p: Practitioner) -> None:
    print("\nFORECAST  mn10:46")
    for pali, en in SCHEDULE:
        tag = "TEXT" if en in ("seven years", "six years", "one year", "seven months",
                               "half a month", "seven days") else "PE"
        fruit_pali, fruit_en = expected_fruit(p)
        note("mn10:46", Verb.AVOCA, f"ime cattāro satipaṭṭhāne evaṁ bhāveyya {pali} → {fruit_pali}",
             f"practiced in this way for {en}: one of two fruits may be expected → {fruit_en}", tag)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. DWELL — viharati
# ═══════════════════════════════════════════════════════════════════════════════


def dwell(p: Practitioner, stream: Iterable[Phenomenon]) -> None:
    """[TEXT] viharati is a continuous present. The sutta gives no exit condition.
    [READING] The loop ends only when its input ends. There is no break, no success check,
    no return value. kāye kāyānupassī — each lens observes its object within its own type:
    a feeling seen as a feeling is not re-cast as a body event or a principle."""
    print("\nSETTING  mn10:4.2 (stated once)")
    for pali, en in SETTING:
        note("mn10:4.2", Verb.VIHARATI, pali, en)

    for ph in stream:
        section = SECTIONS.get(ph.kind)
        print(f"\n── {ph.domain} · {section.number if section else '?'} "
              f"{section.pali if section else ph.kind} ──")
        if not p.frame_holds():
            note("mn10:3.2", Verb.VIHARATI, "(ātāpī sampajāno satimā … not all present)",
                 "frame not established; observation recorded, not refused", "READING")
        if section is None or section.domain != ph.domain:
            unmatched(ph, "no section of MN 10 observes this kind in this domain")
            continue
        result = section.run(p, ph)
        if section.run is sivathika:
            rseg, abbrev = result  # type: ignore[misc]
            refrain(ph, rseg, f"{rseg}.2" if abbrev else f"{rseg}.4", abbrev)
        else:
            refrain(ph, section.refrain_seg, section.closing_seg, section.abbreviated)


def satipatthana(p: Practitioner, stream: Iterable[Phenomenon]) -> None:
    uddesa(p)
    dwell(p, stream)
    forecast(p)
    print("\nRING  mn10:47.1 == mn10:2.1")
    assert CLOSING == PURPOSE
    for pali, en in CLOSING:
        note("mn10:47.1", Verb.AVOCA, pali, en)
    print("\nmn10:47.2–47.4 — idamavoca bhagavā. attamanā te bhikkhū bhagavato bhāsitaṁ abhinandunti.")


# ═══════════════════════════════════════════════════════════════════════════════
# 13. LAP_V0 — the prior plate (genno.html §三), kept beneath, with what changed and why
# ═══════════════════════════════════════════════════════════════════════════════

LAP_V0 = [
    ("Mind.states",
     "v0 paired 'contracted' with 'expansive' and listed five pairs. The sutta pairs saṅkhitta/vikkhitta "
     "(constricted/scattered) and mahaggata/amahaggata (expansive/unexpansive), and adds sa-uttara/anuttara, "
     "samāhita/asamāhita, vimutta/avimutta: eight pairs.", "mn10:34.2–34.17"),
    ("Feeling.valences",
     "v0 had three valences. The sutta has nine: each valence plain, of the flesh (sāmisa), "
     "not of the flesh (nirāmisa).", "mn10:32.2–32.10"),
    ("Body",
     "v0 had breath, postures, elements. The sutta also has situational awareness, the thirty-one parts, "
     "and nine charnel stages. In breathing, v0 omitted the verb shift pajānāti → sikkhati.", "mn10:4–31"),
    ("release()",
     "v0 called release() on attachment. The sutta never executes a release. For hindrances and fetters "
     "one knows how abandoning comes about: pahānaṁ hoti, tañca pajānāti.", "mn10:36.4, 40.3"),
    ("Dhammas.observe",
     "v0 checked category membership. The sutta runs a lifecycle per item (hindrances, fetters, factors) "
     "or a thing/origin/ending triple (aggregates).", "mn10:36–44"),
    ("free_of_worldly_desire_and_grief",
     "v0 tested it as a loop condition. In the sutta it is a concomitant quality (vineyya, absolutive).",
     "mn10:3.2"),
    ("return liberation",
     "v0 returned liberation after the loop. The sutta states a forecast of one of two fruits, "
     "branching on remaining substrate, outside the exposition.", "mn10:46"),
    ("refrain",
     "v0 noted arising/passing and 'internally, or externally, or both'. The sutta also has the bare "
     "'atthi kāyo' clause, bounded by knowledge and recollection, and dwelling independent, grasping nothing.",
     "mn10:5.1–5.3"),
    ("what stands",
     "v0's header — 'not a verbatim translation; an extraction of structure' — still holds for this plate. "
     "So does its closing line.", "genno.html §三"),
]


# ═══════════════════════════════════════════════════════════════════════════════
# 14. A SHORT SITTING — demonstration stream. One phenomenon per section, plus one unmatched.
# ═══════════════════════════════════════════════════════════════════════════════

DEMO: list[Phenomenon] = [
    Phenomenon("kāya", "breath", ("in", "dīgha")),
    Phenomenon("kāya", "breath", ("out", "rassa")),
    Phenomenon("kāya", "posture", "sitting"),
    Phenomenon("kāya", "posture", "kneeling"),                          # wildcard branch, 6.2
    Phenomenon("kāya", "activity", "eating"),
    Phenomenon("kāya", "anatomy", "ascending"),
    Phenomenon("kāya", "elements", None, Locus.BOTH),
    Phenomenon("kāya", "charnel", 1, Locus.EXTERNAL),
    Phenomenon("kāya", "charnel", 9, Locus.BOTH, Phase.VANISHING),
    Phenomenon("vedanā", "feeling", ("painful", "not_of_the_flesh"), phase=Phase.ARISING),
    Phenomenon("citta", "mind", "vikkhittaṁ"),
    Phenomenon("dhammā", "hindrance", ("vicikicchā", "present")),
    Phenomenon("dhammā", "hindrance", ("vicikicchā", "abandoning")),
    Phenomenon("dhammā", "aggregate", ("saññā", "origin")),
    Phenomenon("dhammā", "sensebase", ("ear", "contact")),
    Phenomenon("dhammā", "sensebase", ("ear", "non-recurrence")),
    Phenomenon("dhammā", "factor", ("upekkhā", "fulfilment")),
    Phenomenon("dhammā", "truth", "samudaya"),
    Phenomenon("vedanā", "feeling", ("bittersweet", None)),             # outside the nine: held, not coerced
]


if __name__ == "__main__":
    satipatthana(Practitioner(), DEMO)
    print(f"\n{len(TRACE)} notes. {len(UNMATCHED)} held unmatched. "
          f"{REFRAIN_COUNT} refrain sites in the text; {len(LAP_V0)} laps over v0.")
    print("\n鈴は一打で足りる。 The bell needs only one strike.\nka-ateuh.")