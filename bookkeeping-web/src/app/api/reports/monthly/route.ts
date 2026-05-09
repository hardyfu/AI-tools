import { NextRequest, NextResponse } from "next/server";
import { ensureSeedData } from "@/lib/bootstrap";
import { monthRange, toMonthString } from "@/lib/date";
import { prisma } from "@/lib/prisma";

export async function GET(request: NextRequest) {
  const { familyBook } = await ensureSeedData();
  const searchParams = request.nextUrl.searchParams;
  const bookId = searchParams.get("bookId") ?? familyBook.id;
  const month = searchParams.get("month") ?? toMonthString(new Date());

  const { start, end } = monthRange(month);

  const [monthlyTransactions, allUntilMonthEnd] = await Promise.all([
    prisma.transaction.findMany({
      where: { bookId, date: { gte: start, lt: end } },
      include: { category: true },
      orderBy: { date: "asc" },
    }),
    prisma.transaction.findMany({
      where: { bookId, date: { lt: end } },
      select: { type: true, amount: true },
    }),
  ]);

  let income = 0;
  let expense = 0;
  const breakdown = new Map<string, { categoryId: string; categoryName: string; type: string; amount: number }>();

  for (const tx of monthlyTransactions) {
    const amount = Number(tx.amount);
    if (tx.type === "income") income += amount;
    if (tx.type === "expense") expense += amount;

    const existing = breakdown.get(tx.categoryId);
    if (existing) {
      existing.amount += amount;
    } else {
      breakdown.set(tx.categoryId, {
        categoryId: tx.categoryId,
        categoryName: tx.category.name,
        type: tx.type,
        amount,
      });
    }
  }

  let openingFundTotal = 0;
  try {
    const openingFund = await prisma.openingFund.findUnique({ where: { bookId }, include: { buckets: true } });
    const openingFundBucketTotal = (openingFund?.buckets ?? []).reduce(
      (sum, item) => sum + Number(item.amount),
      0,
    );
    openingFundTotal =
      Number(openingFund?.cashAmount ?? 0) +
      Number(openingFund?.wealthAmount ?? 0) +
      openingFundBucketTotal;
  } catch {
    openingFundTotal = 0;
  }

  let runningBalance = openingFundTotal;
  for (const tx of allUntilMonthEnd) {
    const amount = Number(tx.amount);
    runningBalance += tx.type === "income" ? amount : -amount;
  }

  return NextResponse.json({
    month,
    summary: {
      income,
      expense,
      monthBalance: income - expense,
      runningBalance,
      openingFundTotal,
    },
    breakdown: Array.from(breakdown.values()).sort((a, b) => b.amount - a.amount),
  });
}
