"use client";

import { useEffect, useMemo, useState } from "react";
import { currentMonth, formatCurrency } from "@/lib/ui";

type SalaryItem = { itemName: string; amount: number; note?: string };
type SalaryAllocation = {
  id: string;
  month: string;
  salaryAmount: number;
  note?: string | null;
  items: Array<{ id: string; itemName: string; amount: number; note?: string | null }>;
};

export default function SalaryPage() {
  const [allocations, setAllocations] = useState<SalaryAllocation[]>([]);

  const [month, setMonth] = useState(currentMonth());
  const [salaryAmount, setSalaryAmount] = useState("");
  const [note, setNote] = useState("");
  const [items, setItems] = useState<SalaryItem[]>([
    { itemName: "家庭生活", amount: 0 },
    { itemName: "孩子储蓄", amount: 0 },
    { itemName: "理财投入", amount: 0 },
  ]);

  const loadAllocations = async () => {
    const res = await fetch("/api/salary-allocations");
    const data = await res.json();
    setAllocations(data.allocations ?? []);
  };

  useEffect(() => {
    fetch("/api/salary-allocations")
      .then((res) => res.json())
      .then((data) => setAllocations(data.allocations ?? []));
  }, []);

  const itemTotal = useMemo(() => items.reduce((sum, item) => sum + Number(item.amount || 0), 0), [items]);

  const updateItem = (index: number, key: "itemName" | "amount", value: string) => {
    setItems((prev) =>
      prev.map((item, i) =>
        i === index
          ? {
              ...item,
              [key]: key === "amount" ? Number(value) : value,
            }
          : item,
      ),
    );
  };

  const addItem = () => {
    setItems((prev) => [...prev, { itemName: "", amount: 0 }]);
  };

  const onSave = async (event: React.FormEvent) => {
    event.preventDefault();
    const res = await fetch("/api/salary-allocations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        month,
        salaryAmount: Number(salaryAmount),
        note,
        items,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      alert(err.error || "保存失败");
      return;
    }

    await loadAllocations();
  };

  return (
    <div className="space-y-5">
      <section className="card p-4">
        <h1 className="mb-1 text-lg font-semibold">每月工资分配</h1>
        <p className="mb-3 text-sm text-stone-500">默认应用到家庭理财账本，无需选择账本。</p>
        <form onSubmit={onSave} className="space-y-3">
          <div className="grid gap-3 md:grid-cols-3">
            <input type="month" className="input" value={month} onChange={(e) => setMonth(e.target.value)} />
            <input
              type="number"
              className="input"
              placeholder="工资总额"
              value={salaryAmount}
              onChange={(e) => setSalaryAmount(e.target.value)}
              required
            />
            <input className="input" placeholder="备注" value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
          <div className="space-y-2">
            {items.map((item, index) => (
              <div key={index} className="grid gap-2 md:grid-cols-3">
                <input
                  className="input"
                  placeholder="分配项名称"
                  value={item.itemName}
                  onChange={(e) => updateItem(index, "itemName", e.target.value)}
                />
                <input
                  type="number"
                  className="input"
                  placeholder="金额"
                  value={item.amount}
                  onChange={(e) => updateItem(index, "amount", e.target.value)}
                />
                <button type="button" className="btn btn-muted" onClick={() => setItems((prev) => prev.filter((_, i) => i !== index))}>
                  删除分配项
                </button>
              </div>
            ))}
          </div>
          <div className="flex items-center justify-between">
            <button type="button" className="btn btn-muted" onClick={addItem}>
              新增分配项
            </button>
            <div className="text-sm text-stone-600">分配合计: {formatCurrency(itemTotal)}</div>
          </div>
          <button type="submit" className="btn btn-primary">
            保存本月分配
          </button>
        </form>
      </section>

      <section className="card p-4">
        <h2 className="mb-3 text-base font-semibold">历史分配</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {allocations.map((allocation) => (
            <article key={allocation.id} className="rounded-lg border border-stone-200 bg-stone-50 p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="font-medium">{allocation.month}</span>
                <span>{formatCurrency(allocation.salaryAmount)}</span>
              </div>
              <ul className="space-y-1 text-sm text-stone-700">
                {allocation.items.map((item) => (
                  <li key={item.id} className="flex items-center justify-between">
                    <span>{item.itemName}</span>
                    <span>{formatCurrency(item.amount)}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
