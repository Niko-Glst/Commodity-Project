# --- full analysis: every asset and sector against cash since 6 Oct
EX = R["extra"]
pf7 = pd.DataFrame(EX["perf"]).set_index("ticker").drop(index=["MTUM", "USMV"])
x7 = pf7.sort_values("since_oct6")
cash7 = pf7.loc["BIL", "since_oct6"]
fig, ax = plt.subplots(figsize=(7.2, 4.3))
cols7 = ["#898781" if t == "BIL" else (BLUE if v > cash7 else ORANGE) for t, v in x7.since_oct6.items()]
ax.barh(range(len(x7)), x7.since_oct6, color=cols7, height=0.72)
ax.set_yticks(range(len(x7)))
ax.set_yticklabels([f"{n} ({t})" for t, n in zip(x7.index, x7.name)], fontsize=6.6, color=INK2)
for i_, v_ in enumerate(x7.since_oct6):
    ax.text(v_ + (0.004 if v_ >= 0 else -0.004), i_, f"{v_:+.1%}", va="center", ha="left" if v_ >= 0 else "right",
            fontsize=6.2, color=INK)
ax.axvline(0, color=AXIS, lw=0.8)
ax.axvline(cash7, color="#898781", lw=0.8, ls=(0, (3, 2)))
ax.grid(axis="y", visible=False)
ax.grid(axis="x", color=GRID, lw=0.6)
ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
ax.set_xlim(x7.since_oct6.min() - 0.07, x7.since_oct6.max() + 0.06)
ax.legend(handles=[Patch(color=BLUE, label="Above cash"), Patch(color=ORANGE, label="Below cash"),
                   Patch(color="#898781", label="Cash (T-bills)")], loc="lower right", fontsize=7)
c_sectors = save(fig, "r_sectors")

