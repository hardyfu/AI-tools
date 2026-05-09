import { NextRequest, NextResponse } from "next/server";
import { getHoldingAfterTrade, parseTradeType, toAssetHoldingDto, validateNonNegative } from "@/lib/assets";
import { prisma } from "@/lib/prisma";

export async function POST(request: NextRequest) {
  const body = await request.json();

  const holdingId = String(body.holdingId ?? "");
  const tradeType = parseTradeType(body.tradeType);
  const date = new Date(String(body.date ?? ""));
  const quantity = Number(body.quantity ?? 0);
  const price = Number(body.price ?? 0);
  const amount = Number(body.amount ?? quantity * price);
  const fee = Number(body.fee ?? 0);
  const note = body.note ? String(body.note) : null;
  const relationKey = body.relationKey ? String(body.relationKey) : null;

  if (
    !holdingId ||
    Number.isNaN(date.getTime()) ||
    quantity <= 0 ||
    !validateNonNegative([price, amount, fee])
  ) {
    return NextResponse.json({ error: "交易信息不合法" }, { status: 400 });
  }

  const result = await prisma.$transaction(async (tx) => {
    const holding = await tx.assetHolding.findUniqueOrThrow({ where: { id: holdingId } });
    const nextHolding = getHoldingAfterTrade({
      tradeType,
      currentQuantity: holding.quantity,
      currentCostAmount: holding.costAmount,
      currentValue: holding.currentValue,
      quantity,
      amount,
      fee,
    });

    const trade = await tx.assetTrade.create({
      data: {
        holdingId,
        tradeType,
        date,
        quantity,
        price,
        amount,
        fee,
        note,
        relationKey,
      },
    });

    const updatedHolding = await tx.assetHolding.update({
      where: { id: holdingId },
      data: nextHolding,
      include: { trades: { orderBy: { date: "desc" } } },
    });

    return { trade, holding: updatedHolding };
  });

  return NextResponse.json({
    trade: {
      ...result.trade,
      quantity: Number(result.trade.quantity),
      price: Number(result.trade.price),
      amount: Number(result.trade.amount),
      fee: Number(result.trade.fee),
    },
    holding: toAssetHoldingDto(result.holding),
  }, { status: 201 });
}
