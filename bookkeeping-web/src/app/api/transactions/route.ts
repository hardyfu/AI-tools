import { NextRequest, NextResponse } from "next/server";
import { Prisma, TransactionType } from "@prisma/client";
import { ensureSeedData } from "@/lib/bootstrap";
import { monthRange } from "@/lib/date";
import { prisma } from "@/lib/prisma";

export async function GET(request: NextRequest) {
  await ensureSeedData();
  const searchParams = request.nextUrl.searchParams;
  const bookId = searchParams.get("bookId");
  const month = searchParams.get("month");
  const type = searchParams.get("type") as TransactionType | null;
  const categoryId = searchParams.get("categoryId");
  const q = searchParams.get("q");
  const relationKey = searchParams.get("relationKey");
  const dateFrom = searchParams.get("dateFrom");
  const dateTo = searchParams.get("dateTo");
  const limit = Number(searchParams.get("limit") ?? 100);

  const where: Prisma.TransactionWhereInput = {};
  if (bookId) where.bookId = bookId;
  if (type && [TransactionType.income, TransactionType.expense].includes(type)) {
    where.type = type;
  }
  if (categoryId) where.categoryId = categoryId;
  if (relationKey) where.relationKey = { contains: relationKey };
  if (month) {
    const { start, end } = monthRange(month);
    where.date = { gte: start, lt: end };
  }
  if (!month && (dateFrom || dateTo)) {
    const gte = dateFrom ? new Date(`${dateFrom}T00:00:00`) : undefined;
    const lt = dateTo ? new Date(new Date(`${dateTo}T00:00:00`).getTime() + 24 * 60 * 60 * 1000) : undefined;
    where.date = {
      ...(gte && !Number.isNaN(gte.getTime()) ? { gte } : {}),
      ...(lt && !Number.isNaN(lt.getTime()) ? { lt } : {}),
    };
  }
  if (q) {
    where.OR = [
      { note: { contains: q } },
      { relationKey: { contains: q } },
      { category: { name: { contains: q } } },
    ];
  }

  const transactions = await prisma.transaction.findMany({
    where,
    include: { category: true, book: true },
    orderBy: [{ date: "desc" }, { createdAt: "desc" }],
    take: Number.isNaN(limit) ? 100 : Math.min(limit, 5000),
  });

  const data = transactions.map((tx) => ({ ...tx, amount: Number(tx.amount) }));
  return NextResponse.json({ transactions: data });
}

export async function POST(request: NextRequest) {
  await ensureSeedData();
  const body = await request.json();

  const payload = {
    bookId: String(body.bookId ?? ""),
    categoryId: String(body.categoryId ?? ""),
    type: body.type as TransactionType,
    amount: Number(body.amount),
    date: new Date(String(body.date ?? "")),
    note: body.note ? String(body.note) : null,
    relationKey: body.relationKey ? String(body.relationKey) : null,
  };

  if (
    !payload.bookId ||
    !payload.categoryId ||
    ![TransactionType.income, TransactionType.expense].includes(payload.type) ||
    Number.isNaN(payload.amount) ||
    payload.amount <= 0 ||
    Number.isNaN(payload.date.getTime())
  ) {
    return NextResponse.json({ error: "参数不合法" }, { status: 400 });
  }

  const transaction = await prisma.transaction.create({
    data: {
      bookId: payload.bookId,
      categoryId: payload.categoryId,
      type: payload.type,
      amount: payload.amount,
      date: payload.date,
      note: payload.note,
      relationKey: payload.relationKey,
    },
    include: { category: true, book: true },
  });

  return NextResponse.json(
    {
      transaction: {
        ...transaction,
        amount: Number(transaction.amount),
      },
    },
    { status: 201 },
  );
}
