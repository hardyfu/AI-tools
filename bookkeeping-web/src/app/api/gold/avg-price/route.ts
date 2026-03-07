import { NextRequest, NextResponse } from "next/server";
import { fetchFiveBankAverageGoldPrice } from "@/lib/gold";

export async function GET(request: NextRequest) {
  try {
    const grams = Number(request.nextUrl.searchParams.get("grams") ?? 0);
    if (Number.isNaN(grams) || grams < 0) {
      return NextResponse.json({ error: "克重必须是大于等于0的数字" }, { status: 400 });
    }

    const quote = await fetchFiveBankAverageGoldPrice();
    const amount = quote.avgPrice * grams;

    return NextResponse.json({
      grams,
      averagePrice: Number(quote.avgPrice.toFixed(2)),
      amount: Number(amount.toFixed(2)),
      banks: quote.banks.map((item) => ({ bank: item.bank, price: item.price, sourceUrl: item.sourceUrl })),
      fetchedAt: quote.fetchedAt,
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "黄金价格计算失败" },
      { status: 500 },
    );
  }
}
