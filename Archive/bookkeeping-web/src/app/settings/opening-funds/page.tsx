"use client";

import { useEffect, useMemo, useState } from "react";
import { formatCurrency } from "@/lib/ui";

type Book = { id: string; name: "child" | "family"; displayName: string };
type AssetItem = { key: string; name: string; amount: number; editable: boolean };
type GoldQuoteBank = { bank: string; price: number; sourceUrl: string };
type CustomAssetRow = { id: string; name: string; amount: string };
type OpeningFundPayload = {
  openingFund?: {
    assets?: AssetItem[];
    goldWeight?: number;
    goldAvgPrice?: number;
    goldValuation?: number;
    note?: string | null;
  };
  error?: string;
};

async function parseJsonSafe<T>(res: Response): Promise<T | null> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as T;
  } catch {
    return null;
  }
}

function newCustomAssetRow(name = "", amount = "0"): CustomAssetRow {
  return { id: crypto.randomUUID(), name, amount };
}

export default function OpeningFundsPage() {
  const [books, setBooks] = useState<Book[]>([]);
  const [bookId, setBookId] = useState("");

  const [cashAmount, setCashAmount] = useState("0");
  const [wealthAmount, setWealthAmount] = useState("0");
  const [investmentAmount, setInvestmentAmount] = useState("0");
  const [goldWeight, setGoldWeight] = useState("0");
  const [goldAvgPrice, setGoldAvgPrice] = useState("0");
  const [goldValuation, setGoldValuation] = useState("0");
  const [goldBanks, setGoldBanks] = useState<GoldQuoteBank[]>([]);
  const [goldFetchedAt, setGoldFetchedAt] = useState("");

  const [customAssets, setCustomAssets] = useState<CustomAssetRow[]>([]);
  const [fundNote, setFundNote] = useState("");

  const totalOpeningFund = useMemo(() => {
    const baseTotal =
      Number(cashAmount || 0) +
      Number(wealthAmount || 0) +
      Number(investmentAmount || 0) +
      Number(goldValuation || 0);
    const customTotal = customAssets.reduce((sum, item) => sum + Number(item.amount || 0), 0);
    return baseTotal + customTotal;
  }, [cashAmount, wealthAmount, investmentAmount, goldValuation, customAssets]);

  const loadOpeningFund = async (nextBookId: string) => {
    if (!nextBookId) return;
    const res = await fetch(`/api/opening-funds?bookId=${nextBookId}`);
    const data = await parseJsonSafe<OpeningFundPayload>(res);
    if (!data || !("openingFund" in data)) {
      alert(data?.error || "读取起始资金失败");
      return;
    }
    const fund = data.openingFund;
    const assets = fund?.assets ?? [];

    const cash = assets.find((item) => item.key === "cash");
    const wealth = assets.find((item) => item.key === "wealth");
    const investment = assets.find((item) => item.key === "investment");
    const custom = assets.filter((item) => item.editable);

    setCashAmount(String(cash?.amount ?? 0));
    setWealthAmount(String(wealth?.amount ?? 0));
    setInvestmentAmount(String(investment?.amount ?? 0));
    setGoldWeight(String(fund?.goldWeight ?? 0));
    setGoldAvgPrice(String(fund?.goldAvgPrice ?? 0));
    setGoldValuation(String(fund?.goldValuation ?? 0));
    setCustomAssets(custom.map((item) => newCustomAssetRow(item.name, String(item.amount))));
    setFundNote(String(fund?.note ?? ""));
    setGoldBanks([]);
    setGoldFetchedAt("");
  };

  useEffect(() => {
    const init = async () => {
      const res = await fetch("/api/books");
      const data = await res.json();
      const nextBooks = data.books as Book[];
      setBooks(nextBooks);
      const family = nextBooks.find((book) => book.name === "family");
      const nextBookId = family?.id || nextBooks[0]?.id || "";
      setBookId(nextBookId);
      if (nextBookId) {
        await loadOpeningFund(nextBookId);
      }
    };
    void init();
  }, []);

  const onAddCustomAsset = () => {
    setCustomAssets((prev) => [...prev, newCustomAssetRow()]);
  };

  const onChangeCustomAsset = (index: number, key: "name" | "amount", value: string) => {
    setCustomAssets((prev) =>
      prev.map((item, i) => {
        if (i !== index) return item;
        return { ...item, [key]: value };
      }),
    );
  };

  const onRemoveCustomAsset = (index: number) => {
    setCustomAssets((prev) => prev.filter((_, i) => i !== index));
  };

  const onComputeGold = async () => {
    const grams = Number(goldWeight || 0);
    if (Number.isNaN(grams) || grams < 0) {
      alert("黄金克重必须是大于等于0的数字");
      return;
    }

    const res = await fetch(`/api/gold/avg-price?grams=${grams}`);
    const data = await parseJsonSafe<{
      error?: string;
      averagePrice?: number;
      amount?: number;
      banks?: GoldQuoteBank[];
      fetchedAt?: string;
    }>(res);
    if (!data) {
      alert("黄金价格计算失败");
      return;
    }
    if (!res.ok) {
      alert(data.error || "黄金价格计算失败");
      return;
    }

    setGoldAvgPrice(String(data.averagePrice ?? 0));
    setGoldValuation(String(data.amount ?? 0));
    setGoldBanks((data.banks ?? []) as GoldQuoteBank[]);
    setGoldFetchedAt(String(data.fetchedAt ?? ""));
  };

  const onSaveOpeningFund = async (event: React.FormEvent) => {
    event.preventDefault();
    const res = await fetch("/api/opening-funds", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        bookId,
        cashAmount: Number(cashAmount || 0),
        wealthAmount: Number(wealthAmount || 0),
        investmentAmount: Number(investmentAmount || 0),
        goldWeight: Number(goldWeight || 0),
        goldAvgPrice: Number(goldAvgPrice || 0),
        goldValuation: Number(goldValuation || 0),
        customAssets: customAssets
          .map((item) => ({ name: item.name.trim(), amount: Number(item.amount || 0) }))
          .filter((item) => item.name.length > 0),
        note: fundNote,
      }),
    });
    if (!res.ok) {
      const err = await parseJsonSafe<{ error?: string }>(res);
      alert(err?.error || "保存失败");
      return;
    }
    await loadOpeningFund(bookId);
    alert("起始资金已保存");
  };

  return (
    <div className="space-y-5">
      <section className="card p-4">
        <h1 className="mb-1 text-lg font-semibold">起始资金设置</h1>
        <p className="mb-3 text-sm text-stone-500">用于设置每个账本的期初余额，累计余额会自动包含这些金额。</p>
        <form onSubmit={onSaveOpeningFund} className="space-y-3">
          <div className="grid gap-3 md:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs text-stone-500">账本</label>
              <select
                className="input"
                value={bookId}
                onChange={(e) => {
                  const nextBookId = e.target.value;
                  setBookId(nextBookId);
                  void loadOpeningFund(nextBookId);
                }}
              >
                {books.map((book) => (
                  <option key={book.id} value={book.id}>
                    {book.displayName}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-stone-500">现金</label>
              <input type="number" min="0" step="0.01" className="input" value={cashAmount} onChange={(e) => setCashAmount(e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-xs text-stone-500">理财</label>
              <input type="number" min="0" step="0.01" className="input" value={wealthAmount} onChange={(e) => setWealthAmount(e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-xs text-stone-500">投资</label>
              <input type="number" min="0" step="0.01" className="input" value={investmentAmount} onChange={(e) => setInvestmentAmount(e.target.value)} />
            </div>
          </div>

          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
            <h2 className="mb-2 text-sm font-semibold text-amber-800">黄金投资估值</h2>
            <div className="grid gap-3 md:grid-cols-4">
              <div>
                <label className="mb-1 block text-xs text-stone-600">黄金克重（g）</label>
                <input type="number" min="0" step="0.01" className="input" value={goldWeight} onChange={(e) => setGoldWeight(e.target.value)} />
              </div>
              <div>
                <label className="mb-1 block text-xs text-stone-600">五大行均价（元/克）</label>
                <input type="number" min="0" step="0.01" className="input" value={goldAvgPrice} onChange={(e) => setGoldAvgPrice(e.target.value)} />
              </div>
              <div>
                <label className="mb-1 block text-xs text-stone-600">黄金估值金额（元）</label>
                <input type="number" min="0" step="0.01" className="input" value={goldValuation} onChange={(e) => setGoldValuation(e.target.value)} />
              </div>
              <div className="flex items-end">
                <button type="button" className="btn btn-primary w-full" onClick={() => void onComputeGold()}>
                  计算黄金资产
                </button>
              </div>
            </div>
            {goldBanks.length > 0 && (
              <div className="mt-2 text-xs text-stone-600">
                <p className="mb-1">五大行价格明细：</p>
                <p>{goldBanks.map((item) => `${item.bank} ${item.price}元/克`).join(" | ")}</p>
                {goldFetchedAt && <p className="mt-1">抓取时间：{new Date(goldFetchedAt).toLocaleString()}</p>}
              </div>
            )}
          </div>

          <div className="space-y-2 rounded-lg border border-stone-200 bg-stone-50 p-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-stone-700">自定义资产项</h2>
              <button type="button" className="btn btn-muted" onClick={onAddCustomAsset}>
                新增资产项
              </button>
            </div>
            {customAssets.length === 0 && <p className="text-sm text-stone-500">暂无自定义资产项</p>}
            {customAssets.map((item, index) => (
              <div key={item.id} className="grid gap-2 md:grid-cols-3">
                <input className="input" placeholder="例如：基金账户" value={item.name} onChange={(e) => onChangeCustomAsset(index, "name", e.target.value)} />
                <input type="number" min="0" step="0.01" className="input" placeholder="金额" value={item.amount} onChange={(e) => onChangeCustomAsset(index, "amount", e.target.value)} />
                <button type="button" className="btn btn-danger" onClick={() => onRemoveCustomAsset(index)}>
                  删除
                </button>
              </div>
            ))}
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <input className="input" placeholder="备注（可选）" value={fundNote} onChange={(e) => setFundNote(e.target.value)} />
            <div className="flex items-center justify-end rounded-md border border-stone-200 bg-white px-3 text-sm text-stone-700">
              起始资金总额: {formatCurrency(totalOpeningFund)}
            </div>
          </div>

          <button type="submit" className="btn btn-primary">
            保存起始资金
          </button>
        </form>
      </section>
    </div>
  );
}
