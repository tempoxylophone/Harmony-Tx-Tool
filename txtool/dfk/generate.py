#!/usr/bin/env python3
"""
 Copyright 2021 Paul Willworth <ioscode@gmail.com>
"""
from datetime import timezone, datetime
import contracts
from constants import KOINLY_UNIVERSAL_FORMAT
from koinly import KoinlyInterpreter
from harmony import DexPriceManager


def get_csv(records, format: str = KOINLY_UNIVERSAL_FORMAT) -> str:
    eventRecords = records["events"]
    response = KoinlyInterpreter.get_csv_row_header()

    DexPriceManager.initialize_static_price_manager(eventRecords["wallet"])

    for record in eventRecords["tavern"]:
        blockDateStr = parse_utc_ts(record.timestamp)
        txFee = ""
        txFeeCurrency = ""
        if hasattr(record, "fiatFeeValue"):
            txFee = record.fiatFeeValue
            txFeeCurrency = "USD"
        if record.event in ["sale", "hire"]:
            sentAmount = ""
            sentType = ""
            rcvdAmount = record.coinCost
            rcvdType = contracts.getAddressName(record.coinType)

        label = ""

        response += ",".join(
            (
                blockDateStr,
                str(sentAmount),
                sentType,
                str(rcvdAmount),
                rcvdType,
                str(txFee),
                txFeeCurrency,
                str(record.fiatAmount),
                record.fiatType,
                label,
                "NFT {0} {1}".format(record.itemID, record.event),
                record.txHash,
                "\n",
            )
        )

    for record in eventRecords["swaps"]:
        blockDateStr = parse_utc_ts(record.timestamp)
        txFee = ""
        txFeeCurrency = ""
        if hasattr(record, "fiatFeeValue"):
            txFee = record.fiatFeeValue
            txFeeCurrency = "USD"
        response += ",".join(
            (
                blockDateStr,
                str(record.swapAmount),
                contracts.getAddressName(record.swapType),
                str(record.receiveAmount),
                contracts.getAddressName(record.receiveType),
                str(txFee),
                txFeeCurrency,
                str(record.fiatSwapValue),
                record.fiatType,
                "",
                "swap",
                record.txHash,
                "\n",
            )
        )

    for record in eventRecords["liquidity"]:
        blockDateStr = parse_utc_ts(record.timestamp)
        txFee = ""
        txFeeCurrency = ""
        if hasattr(record, "fiatFeeValue"):
            txFee = record.fiatFeeValue
            txFeeCurrency = "USD"

        if record.action == "withdraw":
            response += ",".join(
                (
                    blockDateStr,
                    "",
                    "",
                    str(record.coin1Amount),
                    contracts.getAddressName(record.coin1Type),
                    str(txFee),
                    txFeeCurrency,
                    str(record.coin1FiatValue),
                    record.fiatType,
                    "",
                    "{0} {1} to {2}".format(
                        record.action,
                        record.poolAmount,
                        contracts.getAddressName(record.poolAddress),
                    ),
                    record.txHash,
                    "\n",
                )
            )
            response += ",".join(
                (
                    blockDateStr,
                    "",
                    "",
                    str(record.coin2Amount),
                    contracts.getAddressName(record.coin2Type),
                    str(txFee),
                    txFeeCurrency,
                    str(record.coin1FiatValue),
                    record.fiatType,
                    "",
                    "{0} {1} to {2}".format(
                        record.action,
                        record.poolAmount,
                        contracts.getAddressName(record.poolAddress),
                    ),
                    record.txHash,
                    "\n",
                )
            )
        else:
            response += ",".join(
                (
                    blockDateStr,
                    str(record.coin1Amount),
                    contracts.getAddressName(record.coin1Type),
                    "",
                    "",
                    str(txFee),
                    txFeeCurrency,
                    str(record.coin1FiatValue),
                    record.fiatType,
                    "",
                    "{0} {1} to {2}".format(
                        record.action,
                        record.poolAmount,
                        contracts.getAddressName(record.poolAddress),
                    ),
                    record.txHash,
                    "\n",
                )
            )
            response += ",".join(
                (
                    blockDateStr,
                    str(record.coin2Amount),
                    contracts.getAddressName(record.coin2Type),
                    "",
                    "",
                    str(txFee),
                    txFeeCurrency,
                    str(record.coin1FiatValue),
                    record.fiatType,
                    "",
                    "{0} {1} to {2}".format(
                        record.action,
                        record.poolAmount,
                        contracts.getAddressName(record.poolAddress),
                    ),
                    record.txHash,
                    "\n",
                )
            )
    for record in eventRecords["gardens"]:
        blockDateStr = parse_utc_ts(record.timestamp)
        txFee = ""
        txFeeCurrency = ""
        if hasattr(record, "fiatFeeValue"):
            txFee = record.fiatFeeValue
            txFeeCurrency = "USD"
        if record.event == "deposit":
            sentAmount = record.coinAmount
            sentType = contracts.getAddressName(record.coinType)
            rcvdAmount = ""
            rcvdType = ""
        else:
            sentAmount = ""
            sentType = ""
            rcvdAmount = record.coinAmount
            rcvdType = contracts.getAddressName(record.coinType)
        label = ""  # KoinlyInterpreter.getRecordLabel(format, "tavern", record.event)
        response += ",".join(
            (
                blockDateStr,
                str(sentAmount),
                sentType,
                str(rcvdAmount),
                rcvdType,
                str(txFee),
                txFeeCurrency,
                str(record.fiatValue),
                record.fiatType,
                label,
                record.event,
                record.txHash,
                "\n",
            )
        )

    for record in eventRecords["bank"]:
        blockDateStr = parse_utc_ts(record.timestamp)
        txFee = ""
        txFeeCurrency = ""
        if hasattr(record, "fiatFeeValue"):
            txFee = record.fiatFeeValue
            print(txFee)
            txFeeCurrency = "USD"

        if record.action == "deposit":
            sentAmount = record.coinAmount
            sentType = contracts.getAddressName(record.coinType)
            rcvdAmount = record.coinAmount / record.xRate
            rcvdType = "xJewel"
        else:
            sentAmount = record.coinAmount / record.xRate
            sentType = "xJewel"
            rcvdAmount = record.coinAmount
            rcvdType = contracts.getAddressName(record.coinType)

        response += ",".join(
            (
                blockDateStr,
                str(sentAmount),
                sentType,
                str(rcvdAmount),
                rcvdType,
                str(txFee),
                txFeeCurrency,
                str(record.fiatValue),
                record.fiatType,
                "",
                "bank {0}".format(record.action),
                record.txHash,
                "\n",
            )
        )

    for record in eventRecords["alchemist"]:
        blockDateStr = parse_utc_ts(record.timestamp)
        txFee = ""
        txFeeCurrency = ""
        if hasattr(record, "fiatFeeValue"):
            txFee = record.fiatFeeValue
            txFeeCurrency = "USD"
        response += ",".join(
            (
                blockDateStr,
                "",
                '"' + record.craftingCosts + '"',
                str(record.craftingAmount),
                contracts.getAddressName(record.craftingType),
                str(txFee),
                txFeeCurrency,
                str(record.fiatValue),
                record.fiatType,
                "ignored",
                "potion crafting",
                record.txHash,
                "\n",
            )
        )

    for record in eventRecords["airdrops"]:
        blockDateStr = parse_utc_ts(record.timestamp)
        txFee = ""
        txFeeCurrency = ""
        if hasattr(record, "fiatFeeValue"):
            txFee = record.fiatFeeValue
            txFeeCurrency = "USD"

        response += ",".join(
            (
                blockDateStr,
                "",
                "",
                str(record.tokenAmount),
                contracts.getAddressName(record.tokenReceived),
                str(txFee),
                txFeeCurrency,
                str(record.fiatValue),
                record.fiatType,
                "airdrop",
                "",
                record.txHash,
                "\n",
            )
        )

    for record in eventRecords["quests"]:
        blockDateStr = parse_utc_ts(record.timestamp)
        txFee = ""
        txFeeCurrency = ""
        if hasattr(record, "fiatFeeValue"):
            txFee = record.fiatFeeValue
            txFeeCurrency = "USD"

        response += ",".join(
            (
                blockDateStr,
                "",
                "",
                str(record.rewardAmount),
                contracts.getAddressName(record.rewardType),
                str(txFee),
                txFeeCurrency,
                str(record.fiatValue),
                record.fiatType,
                "reward",
                "quest",
                record.txHash,
                "\n",
            )
        )

    for record in eventRecords["wallet"]:
        response += record.to_csv_row(KoinlyInterpreter.KOINLY_USE_ONE_ADDRESS_FORMAT)

    if "lending" in eventRecords:
        for record in eventRecords["lending"]:
            blockDateStr = parse_utc_ts(record.timestamp)
            txFee = ""
            txFeeCurrency = ""
            if hasattr(record, "fiatFeeValue"):
                txFee = record.fiatFeeValue
                txFeeCurrency = "USD"

            if record.event in ["redeem", "borrow"]:
                sentAmount = ""
                sentType = ""
                rcvdAmount = record.coinAmount
                rcvdType = contracts.getAddressName(record.coinType)
            else:
                sentAmount = record.coinAmount
                sentType = contracts.getAddressName(record.coinType)
                rcvdAmount = ""
                rcvdType = ""

            response += ",".join(
                (
                    blockDateStr,
                    str(sentAmount),
                    sentType,
                    str(rcvdAmount),
                    rcvdType,
                    str(txFee),
                    txFeeCurrency,
                    str(record.fiatValue),
                    record.fiatType,
                    "",
                    "lending {0}".format(record.event),
                    record.txHash,
                    "\n",
                )
            )

    return response


def parse_utc_ts(timestamp: int, csv_format: str = KOINLY_UNIVERSAL_FORMAT) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S %Z"
    )
