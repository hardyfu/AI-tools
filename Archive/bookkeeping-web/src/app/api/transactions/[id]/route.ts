import { NextRequest, NextResponse } from "next/server";
import { TransactionType } from "@prisma/client";
import { prisma } from "@/lib/prisma";

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await request.json();

  const data: {
    bookId?: string;
    categoryId?: string;
    type?: TransactionType;
    amount?: number;
    date?: Date;
    note?: string | null;
    relationKey?: string | null;
  } = {};

  if (body.bookId) data.bookId = String(body.bookId);
  if (body.categoryId) data.categoryId = String(body.categoryId);
  if (body.type && [TransactionType.income, TransactionType.expense].includes(body.type)) {
    data.type = body.type;
  }
  if (body.amount !== undefined) data.amount = Number(body.amount);
  if (body.date) data.date = new Date(String(body.date));
  if (body.note !== undefined) data.note = body.note ? String(body.note) : null;
  if (body.relationKey !== undefined) {
    data.relationKey = body.relationKey ? String(body.relationKey) : null;
  }

  const transaction = await prisma.transaction.update({
    where: { id },
    data,
    include: { category: true, book: true },
  });

  return NextResponse.json({
    transaction: {
      ...transaction,
      amount: Number(transaction.amount),
    },
  });
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  await prisma.transaction.delete({ where: { id } });
  return NextResponse.json({ ok: true });
}
