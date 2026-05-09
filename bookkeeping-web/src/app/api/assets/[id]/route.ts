import { NextRequest, NextResponse } from "next/server";
import { parseAssetType, toAssetHoldingDto, validateNonNegative } from "@/lib/assets";
import { prisma } from "@/lib/prisma";

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await request.json();

  const quantity = body.quantity === undefined ? undefined : Number(body.quantity);
  const costAmount = body.costAmount === undefined ? undefined : Number(body.costAmount);
  const currentPrice = body.currentPrice === undefined ? undefined : Number(body.currentPrice);
  const currentValue = body.currentValue === undefined ? undefined : Number(body.currentValue);
  const numericValues = [quantity, costAmount, currentPrice, currentValue].filter(
    (value): value is number => value !== undefined,
  );

  if (!validateNonNegative(numericValues)) {
    return NextResponse.json({ error: "资产金额信息不合法" }, { status: 400 });
  }

  const holding = await prisma.assetHolding.update({
    where: { id },
    data: {
      ...(body.bookId ? { bookId: String(body.bookId) } : {}),
      ...(body.type ? { type: parseAssetType(body.type) } : {}),
      ...(body.name !== undefined ? { name: String(body.name).trim() } : {}),
      ...(quantity !== undefined ? { quantity } : {}),
      ...(costAmount !== undefined ? { costAmount } : {}),
      ...(currentPrice !== undefined ? { currentPrice } : {}),
      ...(currentValue !== undefined ? { currentValue } : {}),
      ...(body.note !== undefined ? { note: body.note ? String(body.note) : null } : {}),
      ...(body.isActive !== undefined ? { isActive: Boolean(body.isActive) } : {}),
    },
  });

  return NextResponse.json({ holding: toAssetHoldingDto(holding) });
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  await prisma.assetHolding.update({ where: { id }, data: { isActive: false } });
  return NextResponse.json({ ok: true });
}
