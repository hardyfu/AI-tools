import { NextRequest, NextResponse } from "next/server";
import { ensureSeedData } from "@/lib/bootstrap";
import { prisma } from "@/lib/prisma";

export async function GET(request: NextRequest) {
  const { familyBook, childBook } = await ensureSeedData();
  const params = request.nextUrl.searchParams;
  const scope = params.get("scope");
  const bookId = params.get("bookId");

  let targetBookIds: string[] = [];
  if (scope === "all") {
    targetBookIds = [familyBook.id, childBook.id];
  } else if (bookId) {
    targetBookIds = [bookId];
  } else {
    targetBookIds = [familyBook.id];
  }

  const funds = await prisma.openingFund.findMany({
    where: { bookId: { in: targetBookIds } },
    include: { buckets: true },
  });

  const totals = new Map<string, number>();
  const add = (name: string, amount: number) => {
    totals.set(name, (totals.get(name) ?? 0) + amount);
  };

  for (const fund of funds) {
    add("现金", Number(fund.cashAmount));
    add("理财", Number(fund.wealthAmount));
    add("投资", Number(fund.investmentAmount));
    add("黄金投资", Number(fund.goldValuation));
    for (const bucket of fund.buckets) {
      add(bucket.name, Number(bucket.amount));
    }
  }

  if (!totals.has("现金")) add("现金", 0);
  if (!totals.has("理财")) add("理财", 0);
  if (!totals.has("投资")) add("投资", 0);
  if (!totals.has("黄金投资")) add("黄金投资", 0);

  const assets = Array.from(totals.entries())
    .map(([name, amount]) => ({ name, amount }))
    .sort((a, b) => b.amount - a.amount);
  const total = assets.reduce((sum, item) => sum + item.amount, 0);

  return NextResponse.json({ assets, total });
}
