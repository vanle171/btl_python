(function () {
    const rootElement = document.getElementById("react-pond-explorer");
    const dataElement = document.getElementById("featured-ponds-data");

    if (!rootElement || !dataElement || !window.React || !window.ReactDOM) {
        return;
    }

    const { createElement: h, useMemo, useState } = window.React;
    const { createRoot } = window.ReactDOM;
    const ponds = JSON.parse(dataElement.textContent || "[]");

    function formatMoney(value) {
        return new Intl.NumberFormat("vi-VN").format(value || 0) + " VND";
    }

    function ExplorerApp() {
        const districtOptions = useMemo(() => {
            return ["Tất cả", ...new Set(ponds.map((pond) => pond.district))];
        }, []);

        const [selectedDistrict, setSelectedDistrict] = useState("Tất cả");

        const filteredPonds = useMemo(() => {
            if (selectedDistrict === "Tất cả") {
                return ponds;
            }
            return ponds.filter((pond) => pond.district === selectedDistrict);
        }, [selectedDistrict]);

        const stats = useMemo(() => {
            const availableSlots = filteredPonds.reduce((sum, pond) => sum + (pond.available_slots || 0), 0);
            const averagePrice = filteredPonds.length
                ? Math.round(filteredPonds.reduce((sum, pond) => sum + (pond.price_per_slot || 0), 0) / filteredPonds.length)
                : 0;

            return [
                { label: "Hồ nổi bật", value: filteredPonds.length },
                { label: "Chỗ trống", value: availableSlots },
                { label: "Giá trung bình", value: formatMoney(averagePrice) },
            ];
        }, [filteredPonds]);

        return h("section", { className: "react-explorer" }, [
            h("div", { className: "react-explorer__head", key: "head" }, [
                h("div", { key: "copy" }, [
                    h("span", { className: "react-kicker" }, "Khám phá bằng React"),
                    h("h3", { className: "react-title" }, "Lọc nhanh hồ câu nổi bật theo khu vực"),
                    h(
                        "p",
                        { className: "react-subtitle" },
                        "Giữ luồng render của Flask, bổ sung lớp giao diện React để trải nghiệm tìm hồ câu trực quan hơn."
                    ),
                ]),
                h(
                    "div",
                    { className: "react-stats", key: "stats" },
                    stats.map((item) =>
                        h("div", { className: "react-stat-box", key: item.label }, [
                            h("span", { className: "react-stat-box__label" }, item.label),
                            h("strong", { className: "react-stat-box__value" }, String(item.value)),
                        ])
                    )
                ),
            ]),
            h(
                "div",
                { className: "react-filter-row", key: "filters" },
                districtOptions.map((district) =>
                    h(
                        "button",
                        {
                            type: "button",
                            key: district,
                            className:
                                "react-filter-chip" +
                                (selectedDistrict === district ? " react-filter-chip--active" : ""),
                            onClick: () => setSelectedDistrict(district),
                        },
                        district
                    )
                )
            ),
            h(
                "div",
                { className: "react-pond-grid", key: "grid" },
                filteredPonds.length
                    ? filteredPonds.map((pond) =>
                          h("article", { className: "react-pond-card", key: pond.id }, [
                              h("img", {
                                  className: "react-pond-card__image",
                                  src: pond.image,
                                  alt: pond.name,
                              }),
                              h("div", { className: "react-pond-card__body" }, [
                                  h("div", { className: "react-pond-card__meta" }, [
                                      h("span", { className: "react-pond-card__district" }, pond.district),
                                      h(
                                          "span",
                                          { className: "react-pond-card__slots" },
                                          "Còn " + pond.available_slots + " chỗ"
                                      ),
                                  ]),
                                  h("h4", { className: "react-pond-card__title" }, pond.name),
                                  h("p", { className: "react-pond-card__address" }, pond.address),
                                  h(
                                      "p",
                                      { className: "react-pond-card__description" },
                                      pond.description.length > 120
                                          ? pond.description.slice(0, 120) + "..."
                                          : pond.description
                                  ),
                                  h("div", { className: "react-pond-card__footer" }, [
                                      h("strong", { className: "react-pond-card__price" }, formatMoney(pond.price_per_slot)),
                                      h(
                                          "a",
                                          {
                                              className: "btn btn-primary",
                                              href: pond.detail_url,
                                          },
                                          "Xem chi tiết"
                                      ),
                                  ]),
                              ]),
                          ])
                      )
                    : h("div", { className: "alert alert-info w-100" }, "Không có hồ câu nào ở bộ lọc này."),
            ),
        ]);
    }

    createRoot(rootElement).render(h(ExplorerApp));
})();
