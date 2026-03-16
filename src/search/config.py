CODE_FIELDS = ["BCODE", "XCODE", "MCODE", "PCODE", "ACODE"]
TEXT_FIELDS = ["DESCR", "MODEL", "BRAND"]

CODE_WEIGHTS = {
    "exact": {
        "BCODE": 100,
        "XCODE": 95,
        "MCODE": 95,
        "PCODE": 95,
        "ACODE": 95,
    },
    "prefix": {
        "BCODE": 80,
        "XCODE": 75,
        "MCODE": 75,
        "PCODE": 75,
        "ACODE": 75,
    },
    "partial": {
        "BCODE": 60,
        "XCODE": 55,
        "MCODE": 55,
        "PCODE": 55,
        "ACODE": 55,
    },
}

TEXT_WEIGHTS = {
    "exact": {
        "BRAND": 70,
        "MODEL": 65,
        "DESCR": 60,
    },
    "prefix": {
        "BRAND": 55,
        "MODEL": 50,
        "DESCR": 45,
    },
    "partial": {
        "BRAND": 40,
        "MODEL": 35,
        "DESCR": 30,
    },
}

TOKEN_TEXT_WEIGHTS = {
    "exact": {
        "BRAND": 18,
        "MODEL": 16,
        "DESCR": 14,
    },
    "prefix": {
        "BRAND": 12,
        "MODEL": 10,
        "DESCR": 8,
    },
    "partial": {
        "BRAND": 7,
        "MODEL": 6,
        "DESCR": 5,
    },
}

TOKEN_CODE_WEIGHTS = {
    "exact": {
        "BCODE": 35,
        "XCODE": 32,
        "MCODE": 32,
        "PCODE": 32,
        "ACODE": 32,
    },
    "prefix": {
        "BCODE": 28,
        "XCODE": 26,
        "MCODE": 26,
        "PCODE": 26,
        "ACODE": 26,
    },
    "partial": {
        "BCODE": 22,
        "XCODE": 20,
        "MCODE": 20,
        "PCODE": 20,
        "ACODE": 20,
    },
}