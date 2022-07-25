#!/usr/bin/env python3
"""

 Copyright 2022 Paul Willworth <ioscode@gmail.com>

"""
KOINLY_ROW_HEADER = 'Date,Sent Amount,Sent Currency,Received Amount,Received Currency,Fee Amount,Fee Currency,Net Worth Amount,Net Worth Currency,Label,Description,TxHash\n'
KOINLY_DATE_FORMAT = '%Y-%m-%d %H:%M:%S %Z'


def koinlyRecordLabel(event_type: str, event: str) -> str:
    if event_type == 'gardens':
        if event == 'staking-reward':
            return 'reward'
        else:
            return 'ignored'
    elif event_type == 'tavern':
        if event == 'sale':
            return 'realized gain'
        elif event == 'hire':
            return 'income'
        else:
            return 'cost'


def getHeaderRow(format) -> str:
    return KOINLY_ROW_HEADER


def getDateFormat(format) -> str:
    return KOINLY_DATE_FORMAT


def getRecordLabel(format, type, event) -> str:
    return koinlyRecordLabel(type, event)
