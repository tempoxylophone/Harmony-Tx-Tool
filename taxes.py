#!/usr/bin/env python3
from decimal import Decimal


# Record for final tax report data
class TaxItem:
    def __init__(
            self,
            txHash,
            sentAmount,
            sentType,
            rcvdAmount,
            rcvdType,
            description,
            category,
            soldDate,
            fiatType='usd',
            proceeds=0,
            acquiredDate=None,
            costs=0,
            term="short",
            txFees=0
    ):
        self.description = description

        # gains, income, or expenses
        self.category = category
        self.acquiredDate = acquiredDate
        self.soldDate = soldDate
        self.fiatType = fiatType
        self.proceeds = Decimal(proceeds)
        self.costs = Decimal(costs)
        self.term = term
        self.amountNotAccounted = Decimal(proceeds)

        # source data points
        self.txHash = txHash
        self.sentAmount = sentAmount
        self.sentType = sentType
        self.rcvdAmount = rcvdAmount
        self.rcvdType = rcvdType
        self.txFees = Decimal(txFees)

    # Only calculate gains assets cost basis was found
    def get_gains(self) -> Decimal:
        if self.proceeds <= 0:
            return Decimal(0)
        
        if hasattr(self, 'txFees'):
            return self.proceeds - self.costs - self.txFees
        else:
            return self.proceeds - self.costs


# A common object structure for combining different types of records
class CostBasisItem:
    def __init__(self, txHash, timestamp, receiveType, receiveAmount, fiatType, fiatReceiveValue):
        self.txHash = txHash
        self.timestamp = timestamp
        self.receiveType = receiveType
        self.receiveAmount = receiveAmount
        self.fiatType = fiatType
        self.fiatReceiveValue = fiatReceiveValue
        self.receiveAmountNotAccounted = receiveAmount
