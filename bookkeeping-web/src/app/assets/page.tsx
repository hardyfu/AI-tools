"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { formatCurrency, todayString } from "@/lib/ui";

type Book = { id: string; name: "child" | "family"; displayName: string };
type AssetType = "fund" | "gold";
type TradeType = "buy" | "sell";
type AssetTrade = {
  id: string;
  tradeType: TradeType;
  date: string;
  quantity: number;
  price: number;
  amount: number;
  fee: number;
  note?: string | null;
  relationKey?: string | null;
};
type AssetHolding = {
  id: string;
  bookId: string;
  type: AssetType;
  name: string;
  quantity: number;
  costAmount: number;
  currentPrice: number;
  currentValue: number;
  note?: string | null;
  isActive: boolean;
  trades?: AssetTrade[];
  book?: { displayName: string };
};

const assetTypeLabels: Record<AssetType, string> = {
  fund: "基金",
  gold: "黄金",
};

async function parseJson<T>(res: Response): Promise<T | null> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as T;
  } catch {
    return null;
  }
}

export default function AssetsPage() {
  const [books, setBooks] = useState<Book[]>([]);
  const [bookId, setBookId] = useState("");
  const [holdings, setHoldings] = useState<AssetHolding[]>([]);

  const [type, setType] = useState<AssetType>("fund");
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("");
  const [costAmount, setCostAmount] = useState("");
  const [currentPrice, setCurrentPrice] = useState("");
  const [currentValue, setCurrentValue] = useState("");
  const [note, setNote] = useState("");

  const [tradeHoldingId, setTradeHoldingId] = useState("");
  const [tradeType, setTradeType] = useState<TradeType>("buy");
  const [tradeDate, setTradeDate] = useState(todayString());
  const [tradeQuantity, setTradeQuantity] = useState("");
  const [tradePrice, setTradePrice] = useState("");
  const [tradeAmount, setTradeAmount] = useState("");
  const [tradeFee, setTradeFee] = useState("0");
  const [tradeRelationKey, setTradeRelationKey] = useState("");
  const [tradeNote, setTradeNote] = useState("");

  const activeHoldings = useMemo(() => holdings.filter((item) => item.isActive), [holdings]);
  const totalValue = useMemo(
    () => activeHoldings.reduce((sum, item) => sum + item.currentValue, 0),
    [activeHoldings],
  );
  const totalCost = useMemo(
    () => activeHoldings.reduce((sum, item) => sum + item.costAmount, 0),
    [activeHoldings],
  );
  const selectedHolding = activeHoldings.find((item) => item.id === tradeHoldingId);

  const loadHoldings = useCallback(async (nextBookId: string) => {
    if (!nextBookId) return;
    const res = await fetch(`/api/assets?bookId=${nextBookId}&includeTrades=1`, { cache: "no-store" });
    const data = await parseJson<{ holdings?: AssetHolding[] }>(res);
    const nextHoldings = data?.holdings ?? [];
    setHoldings(nextHoldings);
    setTradeHoldingId((prev) => (nextHoldings.some((item) => item.id === prev) ? prev : nextHoldings[0]?.id ?? ""));
  }, []);

  useEffect(() => {
    const init = async () => {
      const res = await fetch("/api/books", { cache: "no-store" });
      const data = await res.json();
      const nextBooks = data.books as Book[];
      setBooks(nextBooks);
      const family = nextBooks.find((book) => book.name === "family");
      const nextBookId = family?.id || nextBooks[0]?.id || "";
      setBookId(nextBookId);
      await loadHoldings(nextBookId);
    };
    void init();
  }, [loadHoldings]);

  const onCreateHolding = async (event: React.FormEvent) => {
    event.preventDefault();
    const derivedCurrentValue = Number(currentValue || 0) || Number(quantity || 0) * Number(currentPrice || 0);
    const res = await fetch("/api/assets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        bookId,
        type,
        name,
        quantity: Number(quantity || 0),
        costAmount: Number(costAmount || 0),
        currentPrice: Number(currentPrice || 0),
        currentValue: derivedCurrentValue,
        note,
      }),
    });
    if (!res.ok) {
      const err = await parseJson<{ error?: string }>(res);
      alert(err?.error || "保存失败");
      return;
    }
    setName("");
    setQuantity("");
    setCostAmount("");
    setCurrentPrice("");
    setCurrentValue("");
    setNote("");
    await loadHoldings(bookId);
  };

  const onSaveValuation = async (holding: AssetHolding) => {
    const nextPrice = prompt("当前单价", String(holding.currentPrice));
    if (nextPrice === null) return;
    const nextValue = prompt("当前估值", String(holding.currentValue));
    if (nextValue === null) return;

    await fetch(`/api/assets/${holding.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        currentPrice: Number(nextPrice),
        currentValue: Number(nextValue),
      }),
    });
    await loadHoldings(bookId);
  };

  const onArchive = async (holding: AssetHolding) => {
    if (!confirm(`确认停用 ${holding.name} ?`)) return;
    await fetch(`/api/assets/${holding.id}`, { method: "DELETE" });
    await loadHoldings(bookId);
  };

  const onCreateTrade = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!tradeHoldingId) {
      alert("请先选择持仓");
      return;
    }
    const derivedAmount = Number(tradeAmount || 0) || Number(tradeQuantity || 0) * Number(tradePrice || 0);
    const res = await fetch("/api/asset-trades", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        holdingId: tradeHoldingId,
        tradeType,
        date: tradeDate,
        quantity: Number(tradeQuantity || 0),
        price: Number(tradePrice || 0),
        amount: derivedAmount,
        fee: Number(tradeFee || 0),
        relationKey: tradeRelationKey,
        note: tradeNote,
      }),
    });
    if (!res.ok) {
      const err = await parseJson<{ error?: string }>(res);
      alert(err?.error || "保存失败");
      return;
    }
    setTradeQuantity("");
    setTradePrice("");
    setTradeAmount("");
    setTradeFee("0");
    setTradeRelationKey("");
    setTradeNote("");
    await loadHoldings(bookId);
  };

  return (
    <div className="space-y-5">
      <section className="card p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-lg font-semibold">资产持仓</h1>
            <p className="mt-1 text-sm text-stone-500">基金和黄金放在这里按当前估值进入 Dashboard，不再塞进起始资金。</p>
          </div>
          <select
            className="input max-w-52"
            value={bookId}
            onChange={(e) => {
              const nextBookId = e.target.value;
              setBookId(nextBookId);
              void loadHoldings(nextBookId);
            }}
          >
            {books.map((book) => (
              <option key={book.id} value={book.id}>
                {book.displayName}
              </option>
            ))}
          </select>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <article className="card p-4">
          <p className="text-sm text-stone-500">当前持仓估值</p>
          <p className="mt-1 text-2xl font-semibold text-stone-900">{formatCurrency(totalValue)}</p>
        </article>
        <article className="card p-4">
          <p className="text-sm text-stone-500">持仓成本</p>
          <p className="mt-1 text-2xl font-semibold text-stone-900">{formatCurrency(totalCost)}</p>
        </article>
        <article className="card p-4">
          <p className="text-sm text-stone-500">浮动盈亏</p>
          <p className={`mt-1 text-2xl font-semibold ${totalValue - totalCost >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
            {formatCurrency(totalValue - totalCost)}
          </p>
        </article>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="card p-4">
          <h2 className="mb-3 text-base font-semibold">新增持仓</h2>
          <form onSubmit={onCreateHolding} className="grid gap-3 md:grid-cols-2">
            <select className="input" value={type} onChange={(e) => setType(e.target.value as AssetType)}>
              <option value="fund">基金</option>
              <option value="gold">黄金</option>
            </select>
            <input className="input" placeholder="名称" value={name} onChange={(e) => setName(e.target.value)} required />
            <input type="number" min="0" step="0.0001" className="input" placeholder="份额/克重" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
            <input type="number" min="0" step="0.01" className="input" placeholder="成本金额" value={costAmount} onChange={(e) => setCostAmount(e.target.value)} />
            <input type="number" min="0" step="0.0001" className="input" placeholder="当前单价" value={currentPrice} onChange={(e) => setCurrentPrice(e.target.value)} />
            <input type="number" min="0" step="0.01" className="input" placeholder="当前估值" value={currentValue} onChange={(e) => setCurrentValue(e.target.value)} />
            <input className="input md:col-span-2" placeholder="备注" value={note} onChange={(e) => setNote(e.target.value)} />
            <button type="submit" className="btn btn-primary md:col-span-2">
              保存持仓
            </button>
          </form>
        </article>

        <article className="card p-4">
          <h2 className="mb-3 text-base font-semibold">记录买卖</h2>
          <form onSubmit={onCreateTrade} className="grid gap-3 md:grid-cols-2">
            <select className="input md:col-span-2" value={tradeHoldingId} onChange={(e) => setTradeHoldingId(e.target.value)}>
              {activeHoldings.map((holding) => (
                <option key={holding.id} value={holding.id}>
                  {assetTypeLabels[holding.type]} · {holding.name}
                </option>
              ))}
            </select>
            <select className="input" value={tradeType} onChange={(e) => setTradeType(e.target.value as TradeType)}>
              <option value="buy">买入</option>
              <option value="sell">卖出</option>
            </select>
            <input type="date" className="input" value={tradeDate} onChange={(e) => setTradeDate(e.target.value)} />
            <input type="number" min="0" step="0.0001" className="input" placeholder="份额/克重" value={tradeQuantity} onChange={(e) => setTradeQuantity(e.target.value)} />
            <input type="number" min="0" step="0.0001" className="input" placeholder="成交单价" value={tradePrice} onChange={(e) => setTradePrice(e.target.value)} />
            <input type="number" min="0" step="0.01" className="input" placeholder="成交金额" value={tradeAmount} onChange={(e) => setTradeAmount(e.target.value)} />
            <input type="number" min="0" step="0.01" className="input" placeholder="手续费" value={tradeFee} onChange={(e) => setTradeFee(e.target.value)} />
            <input className="input" placeholder="关联流水ID" value={tradeRelationKey} onChange={(e) => setTradeRelationKey(e.target.value)} />
            <input className="input" placeholder="备注" value={tradeNote} onChange={(e) => setTradeNote(e.target.value)} />
            <button type="submit" className="btn btn-primary md:col-span-2" disabled={!selectedHolding}>
              保存买卖记录
            </button>
          </form>
        </article>
      </section>

      <section className="card p-4">
        <h2 className="mb-3 text-base font-semibold">当前持仓</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-stone-200 text-left text-stone-500">
                <th className="pb-2 pr-3">类型</th>
                <th className="pb-2 pr-3">名称</th>
                <th className="pb-2 pr-3">数量</th>
                <th className="pb-2 pr-3">成本</th>
                <th className="pb-2 pr-3">估值</th>
                <th className="pb-2 pr-3">盈亏</th>
                <th className="pb-2 pr-3">操作</th>
              </tr>
            </thead>
            <tbody>
              {activeHoldings.map((holding) => (
                <tr key={holding.id} className="border-b border-stone-100">
                  <td className="py-2 pr-3">{assetTypeLabels[holding.type]}</td>
                  <td className="py-2 pr-3">{holding.name}</td>
                  <td className="py-2 pr-3">{holding.quantity}</td>
                  <td className="py-2 pr-3">{formatCurrency(holding.costAmount)}</td>
                  <td className="py-2 pr-3">{formatCurrency(holding.currentValue)}</td>
                  <td className={`py-2 pr-3 ${holding.currentValue - holding.costAmount >= 0 ? "text-emerald-700" : "text-rose-700"}`}>
                    {formatCurrency(holding.currentValue - holding.costAmount)}
                  </td>
                  <td className="py-2 pr-3">
                    <div className="flex gap-2">
                      <button type="button" className="btn btn-muted" onClick={() => void onSaveValuation(holding)}>
                        更新估值
                      </button>
                      <button type="button" className="btn btn-danger" onClick={() => void onArchive(holding)}>
                        停用
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {activeHoldings.length === 0 && (
                <tr>
                  <td className="py-4 text-stone-500" colSpan={7}>
                    暂无基金或黄金持仓
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
