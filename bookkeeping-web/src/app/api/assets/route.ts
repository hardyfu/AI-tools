import { NextRequest, NextResponse } from "next/server";
import { ensureSeedData } from "@/lib/bootstrap";
import { getAssetSummary, parseAssetType, toAssetHoldingDto, validateNonNegative } from "@/lib/assets";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  const { familyBook, childBook } = await ensureSeedData();
  const params = request.nextUrl.searchParams;
  const scope = params.get("scope");
  const bookId = params.get("bookId");
  const includeTrades = params.get("includeTrades") === "1";

  if (params.get("summary") === "1") {
    const summary = await getAssetSummary({
      scope: scope === "all" ? "all" : "book",
      bookId,
    });
    return NextResponse.json(summary);
  }

  const targetBookIds =
    scope === "all"
      ? [familyBook.id, childBook.id]
      : [bookId ?? familyBook.id];

  const holdings = await prisma.assetHolding.findMany({
    where: { bookId: { in: targetBookIds } },
    include: {
      book: true,
      trades: includeTrades ? { orderBy: { date: "desc" } } : false,
    },
    orderBy: [{ isActive: "desc" }, { type: "asc" }, { updatedAt: "desc" }],
  });

  return NextResponse.json({ holdings: holdings.map(toAssetHoldingDto) });
}

export async function POST(request: NextRequest) {
  const { familyBook } = await ensureSeedData();
  const body = await request.json();

  const bookId = String(body.bookId ?? familyBook.id);
  const type = parseAssetType(body.type);
  const name = String(body.name ?? "").trim();
  const quantity = Number(body.quantity ?? 0);
  const costAmount = Number(body.costAmount ?? 0);
  const currentPrice = Number(body.currentPrice ?? 0);
  const currentValue = Number(body.currentValue ?? quantity * currentPrice);
  const note = body.note ? String(body.note) : null;

  if (!name || !validateNonNegative([quantity, costAmount, currentPrice, currentValue])) {
    return NextResponse.json({ error: "资产名称和金额信息不合法" }, { status: 400 });
  }

  const holding = await prisma.assetHolding.create({
    data: {
      bookId,
      type,
      name,
      quantity,
      costAmount,
      currentPrice,
      currentValue,
      note,
    },
  });

  return NextResponse.json({ holding: toAssetHoldingDto(holding) }, { status: 201 });
}
