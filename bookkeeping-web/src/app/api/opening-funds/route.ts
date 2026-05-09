import { NextRequest, NextResponse } from "next/server";
import { ensureSeedData } from "@/lib/bootstrap";
import { prisma } from "@/lib/prisma";

type AssetItem = { key: string; name: string; amount: number; editable: boolean };
type CustomAssetInput = { name: string; amount: number };

function toAssets(openingFund: {
  id: string;
  cashAmount: unknown;
  wealthAmount: unknown;
  investmentAmount: unknown;
  goldValuation: unknown;
  buckets: Array<{ id: string; name: string; amount: unknown }>;
} | null): AssetItem[] {
  const base: AssetItem[] = [
    { key: "cash", name: "现金", amount: Number(openingFund?.cashAmount ?? 0), editable: false },
    { key: "wealth", name: "理财", amount: Number(openingFund?.wealthAmount ?? 0), editable: false },
  ];
  const custom =
    openingFund?.buckets.map((bucket) => ({
      key: bucket.id,
      name: bucket.name,
      amount: Number(bucket.amount),
      editable: true,
    })) ?? [];
  return [...base, ...custom];
}

export async function GET(request: NextRequest) {
  try {
    const { familyBook } = await ensureSeedData();
    const bookId = request.nextUrl.searchParams.get("bookId") ?? familyBook.id;

    const openingFund = await prisma.openingFund.findUnique({
      where: { bookId },
      include: { buckets: { orderBy: { createdAt: "asc" } } },
    });
    if (!openingFund) {
      const assets = toAssets(null);
      return NextResponse.json({
        openingFund: {
          bookId,
          cashAmount: 0,
          wealthAmount: 0,
          investmentAmount: 0,
          goldWeight: 0,
          goldAvgPrice: 0,
          goldValuation: 0,
          note: null,
          assets,
          total: assets.reduce((sum, item) => sum + item.amount, 0),
        },
      });
    }

    const assets = toAssets(openingFund);
    return NextResponse.json({
      openingFund: {
        ...openingFund,
        cashAmount: Number(openingFund.cashAmount),
        wealthAmount: Number(openingFund.wealthAmount),
        investmentAmount: Number(openingFund.investmentAmount),
        goldWeight: Number(openingFund.goldWeight),
        goldAvgPrice: Number(openingFund.goldAvgPrice),
        goldValuation: Number(openingFund.goldValuation),
        assets,
        total: assets.reduce((sum, item) => sum + item.amount, 0),
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "读取起始资金失败" },
      { status: 500 },
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const { familyBook } = await ensureSeedData();
    const body = await request.json();

    const bookId = String(body.bookId ?? familyBook.id);
    const cashAmount = Number(body.cashAmount ?? 0);
    const wealthAmount = Number(body.wealthAmount ?? 0);
    const investmentAmount = 0;
    const goldWeight = 0;
    const goldAvgPrice = 0;
    const goldValuation = 0;
    const customAssets: CustomAssetInput[] = Array.isArray(body.customAssets)
      ? body.customAssets
          .map((item: { name?: unknown; amount?: unknown }) => ({
            name: String(item?.name ?? "").trim(),
            amount: Number(item?.amount ?? 0),
          }))
          .filter((item: CustomAssetInput) => item.name.length > 0)
      : [];
    const note = body.note ? String(body.note) : null;

    const invalidBase = [cashAmount, wealthAmount].some((value) => Number.isNaN(value) || value < 0);
    const invalidCustom = customAssets.some((item: CustomAssetInput) => Number.isNaN(item.amount) || item.amount < 0);
    const invalid = invalidBase || invalidCustom;
    if (invalid) {
      return NextResponse.json({ error: "起始资金必须是大于等于0的数字" }, { status: 400 });
    }

    const openingFund = await prisma.$transaction(async (tx) => {
      const saved = await tx.openingFund.upsert({
        where: { bookId },
        update: { cashAmount, wealthAmount, investmentAmount, goldWeight, goldAvgPrice, goldValuation, note },
        create: {
          bookId,
          cashAmount,
          wealthAmount,
          investmentAmount,
          goldWeight,
          goldAvgPrice,
          goldValuation,
          note,
        },
      });
      await tx.openingFundBucket.deleteMany({ where: { openingFundId: saved.id } });
      if (customAssets.length > 0) {
        await tx.openingFundBucket.createMany({
          data: customAssets.map((item: CustomAssetInput) => ({
            openingFundId: saved.id,
            name: item.name,
            amount: item.amount,
          })),
        });
      }
      return tx.openingFund.findUniqueOrThrow({
        where: { id: saved.id },
        include: { buckets: { orderBy: { createdAt: "asc" } } },
      });
    });

    const assets = toAssets(openingFund);
    return NextResponse.json({
      openingFund: {
        ...openingFund,
        cashAmount: Number(openingFund.cashAmount),
        wealthAmount: Number(openingFund.wealthAmount),
        investmentAmount: Number(openingFund.investmentAmount),
        goldWeight: Number(openingFund.goldWeight),
        goldAvgPrice: Number(openingFund.goldAvgPrice),
        goldValuation: Number(openingFund.goldValuation),
        assets,
        total: assets.reduce((sum, item: AssetItem) => sum + item.amount, 0),
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "保存起始资金失败" },
      { status: 500 },
    );
  }
}
