---
type: Specification
title: "Module Spec: Personal Finance & Assets"
description: "Đặc tả nghiệp vụ và domain API cho Module Quản lý Tài chính, Dòng tiền và Tài sản cá nhân."
timestamp: 2026-06-16T00:00:00Z
---

# Module Spec: Personal Finance & Assets

> **Lưu ý:** Tương tự các module khác, User tương tác 100% qua Chat UI (Open WebUI). Giao diện người dùng sẽ là các bảng biểu Markdown được LLM render dựa trên dữ liệu.

## 1. Mục tiêu (Objective)

Quản lý tài chính cá nhân theo triết lý ghi nhận giao dịch thật nhanh, phân loại rõ ràng, theo dõi số dư theo ví/tài khoản, đặt ngân sách, xem báo cáo, quản lý mục tiêu tiết kiệm, nhắc các khoản định kỳ, và theo dõi tài sản/nợ để có bức tranh tài chính đầy đủ.

### 1.1. Source-of-Truth Declaration

```yaml
module: finance
module_type: business_module
canonical_source: cortex_postgresql
capture_buffer: optional_transaction_drafts
derived_sources:
  - reporting_cache
  - optional_rag_index_for_finance_insights
write_policy:
  chat_write: allowed_via_finance_domain_api
  write_external_source: denied_by_default
  confirmation: required_for_ambiguous_or_high_impact
sync_policy:
  import_csv: allowed
  provider_sync: future_scope
```

## 2. Tính năng Cốt lõi (Core Features)

### 2.1. Giao dịch (Transactions)

Đây là lõi quan trọng nhất của module. User phải có thể ghi giao dịch bằng ngôn ngữ tự nhiên qua Chat UI.

- Hỗ trợ 3 loại giao dịch chính:
  - `income`: tiền vào.
  - `expense`: tiền ra.
  - `transfer`: chuyển tiền giữa các ví/tài khoản.
- Mỗi giao dịch tối thiểu gồm:
  - `amount`: số tiền.
  - `currency`: mặc định `VND`, có thể nhập ngoại tệ.
  - `type`: thu, chi, hoặc chuyển khoản.
  - `category_id`: danh mục.
  - `wallet_id`: ví/tài khoản phát sinh.
  - `occurred_at`: ngày giờ giao dịch.
  - `note`: ghi chú tự nhiên.
- Thông tin mở rộng:
  - `with_person`: người/cửa hàng/liên quan đến giao dịch.
  - `location`: địa điểm nếu có.
  - `event_id`: gắn giao dịch với một sự kiện như du lịch, cưới hỏi, dự án cá nhân.
  - `attachment`: ảnh hóa đơn hoặc tài liệu liên quan.
  - `exclude_from_report`: không tính vào báo cáo/ngân sách.
- Cho phép tạo, sửa, xem, tìm kiếm và soft-delete giao dịch.
- Khi thông tin nhập vào bị mơ hồ, Finance API phải trả trạng thái cần bổ sung dữ liệu để Orchestrator hỏi lại user trước khi lưu.

Ví dụ:

```text
Ghi 85k ăn trưa bún bò hôm nay bằng tiền mặt
```

Kết quả chuẩn hóa:

```json
{
  "type": "expense",
  "amount": 85000,
  "currency": "VND",
  "category": "food_and_beverage",
  "wallet": "cash",
  "occurred_at": "today",
  "note": "ăn trưa bún bò"
}
```

### 2.2. Ví/Tài khoản (Wallets)

Wallet là nơi theo dõi nguồn tiền và số dư, tương tự Money Lover.

- Hỗ trợ các loại ví:
  - `basic`: tiền mặt, tài khoản ngân hàng, ví điện tử.
  - `goal`: ví mục tiêu tiết kiệm.
  - `credit`: thẻ tín dụng/khoản đang nợ ngân hàng.
  - `linked`: ví đồng bộ từ ngân hàng trong tương lai.
- Mỗi ví gồm:
  - Tên ví.
  - Loại ví.
  - Tiền tệ mặc định.
  - Số dư ban đầu.
  - Số dư hiện tại.
  - Có tính vào tổng tài sản khả dụng hay không.
  - Trạng thái: active, archived.
- Hỗ trợ chuyển tiền giữa ví mà không làm thay đổi net worth.
- Có "Total Wallet" để xem tổng số tiền khả dụng, trừ nợ thẻ tín dụng nếu có.

### 2.3. Danh mục (Categories)

Category dùng để phân loại giao dịch, làm nền cho báo cáo và ngân sách.

- Có category mặc định cho thu nhập và chi tiêu.
- Hỗ trợ parent/child category.
- Hỗ trợ alias tiếng Việt để `ResolveCategory` gợi ý category từ câu chat đã được Orchestrator parse.
- Cho phép thêm, sửa, ẩn/hiện, merge category.
- Category đặc biệt như transfer, debt, loan, adjustment không nên xóa cứng.

Nhóm chi tiêu mặc định:

- Ăn uống.
- Di chuyển.
- Nhà cửa.
- Hóa đơn & tiện ích.
- Mua sắm.
- Sức khỏe.
- Giáo dục.
- Giải trí.
- Gia đình.
- Công việc.
- Khác.

Nhóm thu nhập mặc định:

- Lương.
- Freelance.
- Thưởng.
- Đầu tư.
- Hoàn tiền.
- Quà tặng.
- Khác.

### 2.4. Ngân sách (Budgets)

Budget giúp kiểm soát chi tiêu theo thời gian.

- Đặt ngân sách cho:
  - Tất cả danh mục chi tiêu.
  - Một category.
  - Nhiều category gộp lại.
  - Một ví cụ thể hoặc tất cả ví.
- Hỗ trợ chu kỳ:
  - Tuần.
  - Tháng.
  - Quý.
  - Năm.
  - Custom range.
- Theo dõi:
  - Số tiền ngân sách.
  - Đã chi.
  - Còn lại.
  - Vượt ngân sách.
  - Tỷ lệ sử dụng.
  - Chi tiêu trung bình/ngày.
  - Dự phóng cuối kỳ.
- Gửi cảnh báo khi đạt 75% ngân sách và khi vượt ngân sách.
- Giao dịch `exclude_from_report` không được tính vào budget.

### 2.5. Báo cáo (Reports)

Report là nơi Finance API tổng hợp dữ liệu tài chính thành structured result để Presentation Adapter render thành Markdown/table/chart-friendly output trong Open WebUI.

- Báo cáo theo thời gian:
  - Ngày.
  - Tuần.
  - Tháng.
  - Quý.
  - Năm.
  - Custom range.
- Báo cáo theo ví:
  - Tất cả ví.
  - Một ví cụ thể.
  - Total Wallet.
- Chỉ số bắt buộc:
  - Opening balance.
  - Ending balance.
  - Total income.
  - Total expense.
  - Net income.
  - Expense breakdown by category.
  - Income breakdown by category.
  - Daily average expense.
  - Top spending categories.
  - Transactions list.
  - Excluded/Other amount.
- Hỗ trợ câu hỏi tự nhiên:
  - "Tháng này tôi tiêu bao nhiêu?"
  - "Tiền đi đâu nhiều nhất?"
  - "So với tháng trước tôi tiêu tăng hay giảm?"
  - "Cho tôi 10 giao dịch gần nhất."

### 2.6. Mục tiêu tiết kiệm (Saving Goals)

Tương đương Goal Wallet trong Money Lover.

- Tạo mục tiêu tiết kiệm với:
  - Tên mục tiêu.
  - Số tiền cần đạt.
  - Ngày kết thúc mong muốn.
  - Ví nguồn hoặc ví mục tiêu.
  - Số tiền đã tiết kiệm.
  - Số tiền còn thiếu.
  - Tiến độ phần trăm.
- Hỗ trợ ghi nhận nạp/rút khỏi goal wallet.
- Báo cáo tiến độ mục tiêu trong chat.

### 2.7. Nợ và Khoản cho vay (Debt & Loan)

Cho phép quản lý tiền mình nợ hoặc người khác nợ mình.

- Theo dõi:
  - Người liên quan.
  - Số tiền gốc.
  - Số tiền đã trả/đã thu.
  - Số tiền còn lại.
  - Ngày đến hạn.
  - Ghi chú.
- Hỗ trợ nhắc thanh toán/thu nợ.
- Khoản trả nợ hoặc thu nợ phải tạo giao dịch tương ứng để dòng tiền không lệch.

### 2.8. Giao dịch định kỳ và nhắc việc (Recurring Transactions & Reminders)

- Hỗ trợ giao dịch lặp lại:
  - Lương hàng tháng.
  - Tiền nhà.
  - Internet.
  - Subscription.
  - Trả góp.
  - Bảo hiểm.
- Cấu hình:
  - Tần suất.
  - Ngày chạy.
  - Ví.
  - Category.
  - Số tiền.
  - Có cần xác nhận trước khi ghi không.
- Finance API cung cấp dữ liệu hạn thanh toán/cảnh báo; Orchestrator hoặc automation layer chịu trách nhiệm gửi nhắc nhở cho user.

### 2.9. Gợi ý nhập liệu nhanh (Smart Suggestions)

Vì giao diện chính là Chat UI, Cortex nên tận dụng lịch sử để nhập nhanh hơn Money Lover dạng form.

- Gợi ý category dựa trên note cũ.
- Gợi ý category dựa trên amount lặp lại trong cùng ví.
- Gợi ý ví mặc định theo category.
- Tự nhận diện:
  - "85k", "1tr2", "1.5 triệu".
  - "hôm qua", "sáng nay", "thứ 2 tuần trước".
  - "ăn trưa", "grab", "cafe", "lương".
- Nếu confidence thấp, Finance API trả trạng thái cần xác nhận; Orchestrator hỏi user thay vì tự lưu.

### 2.10. Quản lý Tài sản Đầu tư (Investments)

Nguyên tắc thiết kế: tài sản đầu tư không được xem như chi tiêu sinh hoạt. Khi mua vàng/cổ phiếu, tiền mặt giảm nhưng net worth không giảm tương ứng; nó chỉ chuyển từ cash sang asset. Vì vậy cần tách 2 lớp:

- `cash transaction`: dòng tiền đi/đến ví tiền.
- `asset transaction`: thay đổi số lượng tài sản nắm giữ.
- `asset holding`: vị thế hiện tại sau nhiều lần mua/bán.
- `asset price`: giá thị trường tại một thời điểm.
- `portfolio valuation`: định giá hiện tại và lãi/lỗ tạm tính.

#### 2.10.1. Loại tài sản hỗ trợ

- `gold`: vàng miếng, vàng nhẫn, vàng trang sức nếu cần.
- `stock`: cổ phiếu.
- `fund`: quỹ/ETF/chứng chỉ quỹ.
- `crypto`: crypto nếu cần.
- `saving_deposit`: tiền gửi tiết kiệm.
- `cash_equivalent`: ngoại tệ hoặc tài sản gần tiền mặt.
- `other`: tài sản khác nhập thủ công.

#### 2.10.2. Asset Master

Mỗi tài sản cần một bản ghi chuẩn để định danh:

- `asset_id`: ID nội bộ.
- `asset_type`: gold, stock, fund, crypto, saving_deposit, other.
- `symbol`: mã giao dịch nếu có, ví dụ `FPT`, `VCB`, `BTC`.
- `name`: tên hiển thị.
- `currency`: VND, USD, v.v.
- `unit`: chỉ, lượng, share, token, certificate.
- `price_source`: nguồn lấy giá, ví dụ manual, provider API, n8n webhook.
- `is_active`: còn theo dõi hay không.

Ví dụ vàng:

```json
{
  "asset_type": "gold",
  "symbol": "SJC_1L",
  "name": "Vàng miếng SJC",
  "currency": "VND",
  "unit": "luong",
  "price_source": "manual"
}
```

Ví dụ cổ phiếu:

```json
{
  "asset_type": "stock",
  "symbol": "FPT",
  "name": "FPT Corporation",
  "currency": "VND",
  "unit": "share",
  "price_source": "market_api"
}
```

#### 2.10.3. Asset Transactions

Mọi hành động mua/bán/nạp/rút/cổ tức/split cần ghi thành asset transaction.

- `buy`: mua tài sản.
- `sell`: bán tài sản.
- `transfer_in`: chuyển tài sản vào hệ thống.
- `transfer_out`: chuyển tài sản ra khỏi hệ thống.
- `dividend`: cổ tức tiền mặt.
- `stock_dividend`: cổ tức bằng cổ phiếu.
- `split`: chia tách cổ phiếu.
- `price_adjustment`: điều chỉnh thủ công nếu nhập sai.

Trường dữ liệu:

- `asset_id`.
- `transaction_type`.
- `quantity`.
- `unit_price`.
- `gross_amount`.
- `fee`.
- `tax`.
- `net_amount`.
- `wallet_id`: ví tiền dùng để mua hoặc nhận tiền bán.
- `occurred_at`.
- `note`.
- `linked_cash_transaction_id`: giao dịch tiền mặt liên quan.

Ví dụ mua vàng:

```json
{
  "transaction_type": "buy",
  "asset": "SJC_1L",
  "quantity": 0.5,
  "unit": "luong",
  "unit_price": 78000000,
  "gross_amount": 39000000,
  "fee": 0,
  "wallet": "Vietcombank",
  "occurred_at": "2026-06-16",
  "note": "Mua 5 chỉ vàng SJC"
}
```

Khi lưu giao dịch này, hệ thống đồng thời tạo cash transaction loại `transfer_to_asset` hoặc `investment_buy` để giảm tiền trong ví, nhưng báo cáo chi tiêu sinh hoạt không được tính đây là expense.

#### 2.10.4. Holdings và Cost Basis

Holding là trạng thái hiện tại của từng tài sản sau khi cộng/trừ các asset transaction.

- `quantity`: số lượng đang nắm giữ.
- `average_cost`: giá vốn trung bình.
- `total_cost`: tổng vốn còn lại.
- `realized_gain`: lãi/lỗ đã chốt sau khi bán.
- `unrealized_gain`: lãi/lỗ tạm tính theo giá hiện tại.
- `current_price`.
- `current_value`.
- `last_priced_at`.

Phương pháp giá vốn mặc định:

- Vàng/crypto/quỹ/cổ phiếu cá nhân: dùng `weighted_average_cost` cho đơn giản.
- Nếu sau này cần báo cáo thuế chi tiết: hỗ trợ thêm FIFO.

Công thức cơ bản:

```text
average_cost = total_remaining_cost / remaining_quantity
current_value = current_quantity * current_market_price
unrealized_gain = current_value - total_remaining_cost
```

#### 2.10.5. Price History

Vì giá vàng/cổ phiếu biến động, không ghi đè giá cũ. Cần lưu lịch sử giá.

- `asset_id`.
- `price`.
- `currency`.
- `price_type`: buy, sell, close, manual, estimated.
- `source`.
- `priced_at`.

Với vàng có thể cần cả giá mua vào và bán ra:

```json
{
  "asset": "SJC_1L",
  "buy_price": 78000000,
  "sell_price": 76000000,
  "currency": "VND",
  "priced_at": "2026-06-16T09:00:00+07:00",
  "source": "manual"
}
```

Quy tắc định giá:

- Nếu đang nắm giữ tài sản, dùng giá có thể bán được để tính thận trọng.
- Vàng dùng `sell_price` làm current value.
- Cổ phiếu dùng close/last price.
- Tài sản không có nguồn giá tự động thì cho phép user nhập thủ công.

#### 2.10.6. Net Worth

Net worth không chỉ là tổng ví tiền. Công thức:

```text
net_worth = cash_wallets + current_asset_values - debts
```

Báo cáo net worth cần hiển thị:

- Cash.
- Gold.
- Stocks/Funds.
- Saving deposits.
- Crypto nếu có.
- Debts/Credit.
- Total net worth.
- Unrealized gain/loss.
- Realized gain/loss trong kỳ.

Ví dụ câu hỏi:

```text
Tài sản ròng hiện tại của tôi bao nhiêu?
```

Presentation Adapter có thể render bảng:

| Nhóm | Giá trị hiện tại | Vốn gốc | Lãi/lỗ |
|---|---:|---:|---:|
| Tiền mặt/tài khoản | 35,000,000 | - | - |
| Vàng | 78,000,000 | 75,000,000 | +3,000,000 |
| Cổ phiếu | 42,000,000 | 45,000,000 | -3,000,000 |
| Nợ | -10,000,000 | - | - |
| **Net worth** | **145,000,000** | | |

## 3. Receipt Extraction Boundary

Finance module không trực tiếp xử lý OCR, vision model, prompt trích xuất hóa đơn, hoặc đọc file upload từ Chat UI. Các bước OCR/LLM extraction thuộc Orchestrator/Document Processing layer. Finance module chỉ nhận dữ liệu hóa đơn đã được trích xuất thành structured payload để validate nghiệp vụ và tạo transaction.

```text
Client (Open WebUI)
  → Upload ảnh/PDF Receipt
  → Cortex API Gateway (Go Backend)
  → Queue xử lý bất đồng bộ
  → OCR Service (PaddleOCR / Cloud API / LiteParse chạy nền)
  → Trả về Text + Layout
  → Document/LLM Extraction layer trích xuất Strict JSON
  → Finance.CreateTransactionFromExtractedReceipt(...)
  → Finance validate tổng tiền, category, wallet, confidence, duplicate
  → Finance lưu transaction hoặc trả trạng thái cần user xác nhận
  → Gửi thông báo hoàn tất vào Chat
```

**Lý do thiết kế:** Tách biệt OCR/LLM extraction khỏi Finance giúp module tài chính deterministic, test được độc lập, và không phụ thuộc vào provider AI. Finance chỉ chịu trách nhiệm business validation sau khi có extracted payload.

## 4. Finance Domain APIs

Finance module expose domain APIs ổn định cho các layer phía trên gọi vào. Module này không xử lý prompt, tool-call schema, chat history hay LLM reasoning. Tool Adapter trong Orchestrator layer sẽ map từ tool-call sang các API dưới đây.

### 4.1. Transaction APIs

- `CreateTransaction(command)`: Ghi nhận giao dịch thu/chi.
- `CreateTransactionFromExtractedReceipt(command)`: Tạo giao dịch từ payload hóa đơn đã được OCR/extract.
- `CreateTransfer(command)`: Chuyển tiền giữa ví/tài khoản.
- `UpdateTransaction(transaction_id, patch)`: Sửa giao dịch.
- `SoftDeleteTransaction(transaction_id, reason)`: Xóa mềm giao dịch.
- `GetTransaction(transaction_id)`: Xem chi tiết giao dịch.
- `ListTransactions(query)`: Liệt kê/tìm kiếm giao dịch.
- `DetectDuplicateTransactions(query)`: Phát hiện giao dịch trùng.
- `AttachReceipt(transaction_id, attachment)`: Gắn ảnh/PDF hóa đơn vào giao dịch.

### 4.2. Wallet & Account APIs

- `CreateWallet(command)`: Tạo ví/tài khoản.
- `UpdateWallet(wallet_id, patch)`: Sửa thông tin ví.
- `ArchiveWallet(wallet_id)`: Lưu trữ ví không còn dùng.
- `ListWallets(query)`: Liệt kê ví.
- `GetWalletBalance(wallet_id, as_of)`: Lấy số dư ví tại một thời điểm.
- `AdjustWalletBalance(command)`: Điều chỉnh số dư khi đối soát.
- `GetTotalWallet(query)`: Tính tổng ví khả dụng.

### 4.3. Category APIs

- `CreateCategory(command)`: Tạo category.
- `UpdateCategory(category_id, patch)`: Sửa category.
- `MergeCategories(source_id, target_id)`: Gộp category.
- `SetCategoryVisibility(category_id, visible)`: Ẩn/hiện category.
- `ListCategories(query)`: Liệt kê category.
- `ResolveCategory(input)`: Gợi ý category từ note, merchant, alias hoặc lịch sử.

### 4.4. Budget APIs

- `CreateBudget(command)`: Tạo ngân sách.
- `UpdateBudget(budget_id, patch)`: Sửa ngân sách.
- `DeleteBudget(budget_id)`: Xóa ngân sách.
- `GetBudgetStatus(query)`: Xem trạng thái ngân sách.
- `ListBudgets(query)`: Liệt kê ngân sách.
- `CalculateBudgetProjection(query)`: Dự phóng chi tiêu cuối kỳ.
- `EvaluateBudgetAlerts(query)`: Tính cảnh báo budget theo ngưỡng.

### 4.5. Report & Insight APIs

- `GetFinancialReport(query)`: Báo cáo thu/chi/net income.
- `GetCategoryBreakdown(query)`: Breakdown theo category.
- `GetMerchantBreakdown(query)`: Breakdown theo merchant.
- `GetTrendReport(query)`: Báo cáo trend theo thời gian.
- `ComparePeriods(query)`: So sánh hai giai đoạn.
- `DetectAnomalies(query)`: Phát hiện giao dịch/khoản chi bất thường.
- `GenerateDigest(query)`: Tạo weekly/monthly digest dạng structured data.

### 4.6. Goal APIs

- `CreateSavingGoal(command)`: Tạo mục tiêu tiết kiệm.
- `UpdateSavingGoal(goal_id, patch)`: Cập nhật mục tiêu.
- `RecordGoalContribution(command)`: Ghi nhận nạp tiền vào mục tiêu.
- `RecordGoalWithdrawal(command)`: Ghi nhận rút tiền khỏi mục tiêu.
- `GetGoalProgress(goal_id)`: Xem tiến độ mục tiêu.
- `CalculateGoalPlan(query)`: Tính số tiền cần tiết kiệm theo kỳ.

### 4.7. Debt, Loan & Credit APIs

- `CreateDebtOrLoan(command)`: Tạo khoản nợ/khoản cho vay.
- `UpdateDebtOrLoan(id, patch)`: Sửa khoản nợ/khoản cho vay.
- `RecordDebtPayment(command)`: Ghi nhận trả/thu nợ.
- `GetDebtStatus(query)`: Xem trạng thái nợ.
- `CalculateDebtPayoffPlan(query)`: Tính kế hoạch trả nợ.
- `CreateCreditAccount(command)`: Tạo tài khoản thẻ tín dụng.
- `GetCreditDueStatus(query)`: Xem hạn thanh toán thẻ tín dụng.

### 4.8. Recurring, Bill & Subscription APIs

- `CreateRecurringTransaction(command)`: Tạo giao dịch định kỳ.
- `UpdateRecurringTransaction(id, patch)`: Sửa giao dịch định kỳ.
- `ListRecurringTransactions(query)`: Liệt kê giao dịch định kỳ.
- `GenerateDueTransactions(query)`: Sinh giao dịch đến hạn.
- `ConfirmDueTransaction(id)`: Xác nhận giao dịch đến hạn.
- `DetectSubscriptions(query)`: Phát hiện subscription từ lịch sử giao dịch.
- `GetBillCalendar(query)`: Lấy lịch hóa đơn.

### 4.9. Forecast APIs

- `GetCashFlowForecast(query)`: Dự báo dòng tiền/số dư tương lai.
- `CalculateLeftoverMoney(query)`: Tính tiền còn có thể tiêu.
- `RunWhatIfScenario(command)`: Chạy kịch bản giả định.
- `ClassifyFixedAndVariableExpenses(query)`: Phân loại fixed/variable expenses.

### 4.10. Investment & Net Worth APIs

- `CreateAsset(command)`: Tạo asset master.
- `UpdateAsset(asset_id, patch)`: Sửa asset master.
- `RecordAssetTransaction(command)`: Ghi mua/bán/chuyển tài sản.
- `ListAssetTransactions(query)`: Liệt kê giao dịch tài sản.
- `GetHoldings(query)`: Lấy vị thế hiện tại.
- `RecordAssetPrice(command)`: Ghi giá tài sản tại thời điểm.
- `GetPriceHistory(query)`: Lấy lịch sử giá.
- `CalculatePortfolioValuation(query)`: Định giá portfolio.
- `GetNetWorth(query)`: Tính tài sản ròng.

### 4.11. Import, Export & Automation APIs

- `ImportTransactions(source, payload)`: Import giao dịch từ CSV/provider.
- `ExportFinanceData(query, format)`: Export CSV/JSON/Markdown.
- `CreateCategorizationRule(command)`: Tạo rule phân loại tự động.
- `ApplyCategorizationRules(query)`: Chạy rule phân loại.
- `CreateBackup(command)`: Tạo backup dữ liệu.
- `RestoreBackup(command)`: Khôi phục backup có kiểm soát.

### 4.12. Tool Adapter Mapping

Tool-call layer chỉ là adapter. Ví dụ:

```text
LLM tool add_transaction
  -> Finance.CreateTransaction(command)

LLM tool get_net_worth
  -> Finance.GetNetWorth(query)

LLM tool record_gold_purchase
  -> Finance.RecordAssetTransaction(command)
  -> Finance.GetNetWorth(query) nếu cần trả thêm bức tranh tài sản
```

Nếu user nói thiếu dữ liệu, Orchestrator hỏi lại. Nếu dữ liệu đủ, Orchestrator gọi Finance API. Finance API chỉ validate nghiệp vụ và trả structured result.

## 5. Business Rules & Invariants

Các rule này là hợp đồng nghiệp vụ của Finance module. Mọi API phải tuân thủ bất kể request đến từ chat, automation, import CSV hay UI khác.

### 5.1. Transaction Rules

- `amount` phải lớn hơn 0.
- `currency` phải hợp lệ và thống nhất với ví hoặc có exchange rate nếu giao dịch đa tiền tệ.
- `income` làm tăng số dư ví.
- `expense` làm giảm số dư ví.
- `transfer` không làm thay đổi net worth, chỉ chuyển giá trị giữa hai ví.
- `transfer` phải có ví nguồn và ví đích khác nhau.
- Giao dịch đã soft-delete không được tính vào báo cáo, budget, forecast, net worth.
- Giao dịch có `exclude_from_report = true` không được tính vào report/budget thông thường, nhưng vẫn phải xuất hiện trong audit và transaction history.
- Giao dịch tạo từ receipt có confidence thấp phải ở trạng thái cần xác nhận trước khi ảnh hưởng số dư/báo cáo chính thức.
- Giao dịch nghi trùng phải được đánh dấu để user xác nhận, không tự động merge/xóa.

### 5.2. Wallet & Balance Rules

- Mỗi transaction phải gắn với ít nhất một ví hợp lệ.
- Số dư ví phải tính lại được từ opening balance + ledger giao dịch + adjustment.
- Adjustment số dư phải có lý do.
- Archive ví không được xóa lịch sử giao dịch.
- Ví archived không nhận giao dịch mới trừ khi user chủ động mở lại hoặc import dữ liệu lịch sử.
- Credit wallet/debt wallet phải được tính ngược chiều với cash wallet trong net worth.

### 5.3. Category & Budget Rules

- Category có transaction lịch sử không được hard-delete; chỉ được ẩn hoặc merge.
- Category merge phải giữ audit trail để report lịch sử vẫn truy vết được.
- Budget chỉ tính các giao dịch phù hợp filter: period, wallet, category, exclude flag.
- Budget rollover phải chỉ rõ phần dư/thâm hụt có chuyển kỳ sau hay không.
- Budget alert là trạng thái tính toán, không tự động tạo transaction.

### 5.4. Investment & Net Worth Rules

- Mua tài sản đầu tư không phải expense sinh hoạt.
- Bán tài sản đầu tư không phải income sinh hoạt, trừ phần lãi/lỗ được report riêng.
- `asset sell` không được vượt quá quantity đang nắm giữ, trừ khi asset cho phép short position.
- Mỗi asset transaction mua/bán phải liên kết với cash movement nếu có dòng tiền phát sinh.
- Giá vốn mặc định dùng weighted average cost.
- Realized gain/loss chỉ phát sinh khi bán tài sản.
- Unrealized gain/loss chỉ là định giá tạm thời theo market price.
- Net worth phải tính từ cash wallets + current asset values - debts/credit liabilities.
- Tài sản không có giá hiện tại phải được đánh dấu stale/unknown thay vì dùng giá đoán không rõ nguồn.

### 5.5. Safety Rules

- Không hard-delete dữ liệu tài chính chính thức.
- Mọi update/delete/merge/import phải có audit event.
- Các thao tác hàng loạt phải hỗ trợ dry-run hoặc preview trước khi commit.
- API phải trả lỗi có cấu trúc khi thiếu dữ liệu, mâu thuẫn nghiệp vụ, hoặc cần user confirmation.
- Dữ liệu nhạy cảm không được gửi ra provider ngoài nếu chưa được policy layer cho phép.

## 6. API Command/Query Contracts

Phần này mô tả contract nghiệp vụ ở mức input/output chính, không thay thế schema kỹ thuật chi tiết.

### 6.1. Common Contract

Mọi command nên có:

- `request_id`: chống gọi lặp/idempotency.
- `source`: chat, import, automation, manual, system.
- `actor`: user/system tạo request.
- `occurred_at` hoặc `effective_at`: thời điểm nghiệp vụ.
- `note`: ghi chú nếu có.
- `confirmation_policy`: auto, require_confirmation, dry_run.

Mọi response nên có:

- `status`: success, needs_confirmation, validation_error, conflict, not_found.
- `entity_id` hoặc `result`.
- `warnings`: cảnh báo không chặn.
- `audit_event_id`: mã audit nếu có ghi thay đổi.
- `next_actions`: gợi ý hành động tiếp theo cho Orchestrator/Presentation Adapter.

### 6.2. CreateTransaction Command

Input chính:

- `type`: income, expense.
- `amount`.
- `currency`.
- `wallet_id`.
- `category_id`.
- `occurred_at`.
- `note`.
- `merchant` hoặc `counterparty` nếu có.
- `attachments` nếu có.
- `exclude_from_report`.

Output chính:

- Transaction đã tạo.
- Số dư ví sau giao dịch.
- Cảnh báo: nghi trùng, category confidence thấp, budget impact.

### 6.3. CreateTransfer Command

Input chính:

- `from_wallet_id`.
- `to_wallet_id`.
- `amount`.
- `currency`.
- `fee` nếu có.
- `occurred_at`.
- `note`.

Output chính:

- Transfer đã tạo.
- Số dư hai ví sau transfer.
- Cảnh báo nếu transfer làm ví nguồn âm.

### 6.4. CreateTransactionFromExtractedReceipt Command

Input chính:

- `receipt_id`.
- `extracted_total`.
- `currency`.
- `merchant`.
- `occurred_at`.
- `line_items`.
- `suggested_category_id`.
- `suggested_wallet_id`.
- `confidence`.
- `attachment_ref`.

Output chính:

- Transaction draft hoặc transaction đã tạo.
- Các field cần user xác nhận.
- Sai lệch giữa line item total và receipt total nếu có.
- Cảnh báo nghi trùng.

### 6.5. RecordAssetTransaction Command

Input chính:

- `asset_id`.
- `transaction_type`: buy, sell, dividend, stock_dividend, split, transfer_in, transfer_out.
- `quantity`.
- `unit_price`.
- `gross_amount`.
- `fee`.
- `tax`.
- `wallet_id`.
- `occurred_at`.
- `note`.

Output chính:

- Asset transaction đã tạo.
- Cash movement liên quan nếu có.
- Holding sau giao dịch.
- Realized gain/loss nếu là lệnh bán.
- Cảnh báo nếu giá thiếu, quantity không đủ, hoặc price stale.

### 6.6. GetFinancialReport Query

Input chính:

- `timeframe`.
- `wallet_ids`.
- `category_ids`.
- `group_by`: category, wallet, merchant, day, month.
- `include_excluded`.
- `include_deleted`: mặc định false.

Output chính:

- Total income.
- Total expense.
- Net income.
- Opening/ending balance.
- Breakdown.
- Top movements.
- Warnings về dữ liệu thiếu, draft, stale hoặc excluded.

### 6.7. GetNetWorth Query

Input chính:

- `as_of`.
- `include_assets`.
- `include_debts`.
- `valuation_policy`: conservative, latest, manual_only.

Output chính:

- Cash total.
- Asset value by group.
- Debt/liability total.
- Net worth.
- Realized/unrealized gain/loss.
- Stale price warnings.

## 7. Audit, Event & Confirmation Requirements

Finance module phải tạo audit/event cho mọi thay đổi có tác động tới dữ liệu tài chính.

- Ghi nhận create/update/delete/merge/import/adjustment/restore.
- Lưu actor, source, timestamp, entity type, entity id, before/after summary.
- Ghi nhận request đến từ LLM/tool adapter hay từ nguồn deterministic khác.
- Ghi nhận user confirmation khi có hành động cần xác nhận.
- Giao dịch draft/pending không được tính như giao dịch chính thức nếu chưa confirm.
- Import hàng loạt phải có import session id để rollback/kiểm tra.
- Audit log không được xóa qua API thông thường.

Các event nghiệp vụ nên có:

- `TransactionCreated`.
- `TransactionUpdated`.
- `TransactionSoftDeleted`.
- `WalletBalanceAdjusted`.
- `BudgetThresholdReached`.
- `RecurringTransactionDue`.
- `DebtPaymentRecorded`.
- `AssetTransactionRecorded`.
- `AssetPriceRecorded`.
- `NetWorthValuationCalculated`.
- `ReceiptTransactionNeedsConfirmation`.

## 8. Price Provider & Valuation Strategy

Giá tài sản biến động phải được quản lý như dữ liệu theo thời điểm, có nguồn và độ tin cậy.

- Không ghi đè giá lịch sử.
- Mỗi price record phải có source và `priced_at`.
- Giá nhập tay phải được đánh dấu `manual`.
- Giá từ provider/n8n webhook phải ghi provider/source.
- Giá quá cũ phải được đánh dấu stale.
- Valuation phải cho biết đang dùng chính sách nào: conservative, latest, manual_only.
- Vàng nên hỗ trợ cả `buy_price` và `sell_price`; net worth mặc định dùng `sell_price` để thận trọng.
- Cổ phiếu/quỹ dùng close/last price theo provider.
- Tài sản không có giá thị trường tự động dùng giá user nhập tay.
- Nếu thiếu giá hiện tại, report phải hiển thị unknown/stale thay vì tự bịa giá.
- Report quá khứ phải dùng giá tại hoặc gần thời điểm `as_of`, không dùng giá hiện tại để viết lại lịch sử.

## 9. Use Case Backlog

Danh sách use case này dùng để chọn scope sau. Tất cả đều thuộc phạm vi finance module, nhưng có thể triển khai theo thứ tự ưu tiên riêng.

### 9.1. Transaction Capture & Cleanup

- Ghi nhanh giao dịch bằng chat tự nhiên.
- Ghi nhiều giao dịch trong một câu.
- Tách một hóa đơn thành nhiều category.
- Gắn ảnh hóa đơn vào giao dịch.
- Tìm giao dịch theo số tiền, note, ví, category, merchant, thời gian.
- Sửa giao dịch bằng câu lệnh tự nhiên.
- Sao chép giao dịch cũ.
- Phát hiện giao dịch trùng.
- Quản lý pending transaction trước khi xác nhận.
- Tạo rule tự động phân loại theo merchant/note/amount.
- Gắn hashtag để phân tích tùy biến.

### 9.2. Wallet, Account & Reconciliation

- Quản lý nhiều ví/tài khoản.
- Chuyển tiền giữa ví.
- Điều chỉnh số dư khi lệch thực tế.
- Đối soát số dư cuối tháng.
- Archive ví không còn dùng.
- Gom nhiều ví thành Total Wallet.
- Phân biệt tài khoản tiền mặt, ngân hàng, ví điện tử, thẻ tín dụng, tiết kiệm, đầu tư.
- Theo dõi số dư khả dụng sau khi trừ các khoản đã lên lịch.

### 9.3. Budgeting & Spending Control

- Ngân sách theo category.
- Ngân sách cho nhiều category gộp lại.
- Ngân sách toàn bộ chi tiêu.
- Budget rollover: phần dư/thâm hụt chuyển sang kỳ sau.
- Cảnh báo theo ngưỡng 50%, 75%, 100%.
- Recommended daily spending.
- Dự phóng cuối kỳ dựa trên tốc độ chi hiện tại.
- So sánh chi tiêu thực tế với ngân sách.
- Phân tích category tăng bất thường.

### 9.4. Bills, Subscriptions & Recurring

- Lịch hóa đơn hằng tháng.
- Theo dõi subscription.
- Nhắc trước hạn thanh toán.
- Phát hiện recurring merchant từ lịch sử giao dịch.
- Cảnh báo subscription tăng giá.
- Gợi ý hủy subscription ít dùng.
- Tự tạo giao dịch định kỳ sau khi user xác nhận.
- Theo dõi ngày lương, ngày trả nợ, ngày thanh toán thẻ tín dụng.

### 9.5. Cash Flow Forecast

- Dự báo số dư tương lai theo thu nhập, hóa đơn, subscription và giao dịch định kỳ.
- Ước tính surplus/deficit cuối tháng.
- Trả lời câu hỏi "Từ giờ đến cuối tháng tôi còn tiêu được bao nhiêu?"
- What-if scenario: "Nếu mua món này 5 triệu thì cuối tháng còn bao nhiêu?"
- Phân biệt fixed expenses và variable expenses.
- Tính leftover money sau khi giữ lại tiền cho hóa đơn và mục tiêu.

### 9.6. Reports & Insights

- Báo cáo thu/chi theo ngày, tuần, tháng, quý, năm.
- Breakdown theo category, merchant, ví, hashtag.
- Trend chi tiêu theo thời gian.
- So sánh tháng này với tháng trước.
- Báo cáo net income.
- Báo cáo excluded/other transactions.
- Top merchants.
- Anomaly detection: khoản chi lạ, phí lạ, giao dịch tăng bất thường.
- Weekly/monthly digest tự động.
- Xuất báo cáo CSV/JSON/Markdown.

### 9.7. Goals & Planning

- Mục tiêu tiết kiệm.
- Emergency fund target.
- Sinking fund cho chi phí lớn định kỳ.
- Goal progress theo số dư ví hoặc planned transactions.
- Tính số tiền cần tiết kiệm mỗi tháng để đạt mục tiêu.
- Cảnh báo mục tiêu bị chậm tiến độ.
- Retirement/simple long-term projection nếu user muốn theo dõi dài hạn.

### 9.8. Debt, Loan & Credit

- Theo dõi khoản mình nợ.
- Theo dõi khoản người khác nợ mình.
- Lịch trả nợ/thu nợ.
- Debt payoff planner.
- So sánh chiến lược trả nợ snowball/avalanche.
- Tính ảnh hưởng của trả thêm mỗi tháng.
- Quản lý thẻ tín dụng: hạn mức, dư nợ, ngày sao kê, ngày đến hạn.
- Cảnh báo nguy cơ trả trễ.

### 9.9. Investments & Net Worth

- Ghi mua/bán vàng.
- Ghi mua/bán cổ phiếu/quỹ/crypto.
- Theo dõi giá vốn trung bình.
- Theo dõi lãi/lỗ đã chốt và chưa chốt.
- Lưu lịch sử giá.
- Cập nhật giá thủ công hoặc qua provider.
- Báo cáo phân bổ portfolio.
- Báo cáo net worth theo thời gian.
- Theo dõi tài sản không niêm yết bằng giá nhập tay.

### 9.10. Automation & Integrations

- Import CSV từ ngân hàng/app khác.
- Export CSV/JSON.
- Đồng bộ ngân hàng read-only nếu sau này có provider phù hợp.
- OCR hóa đơn.
- Nhận webhook từ n8n để cập nhật giá, gửi báo cáo, nhắc hóa đơn.
- Rule engine để tự phân loại giao dịch.
- Backup database định kỳ.
- Multi-device sync nếu có client khác ngoài Open WebUI.

### 9.11. Collaboration & Privacy

- Household/shared wallet cho gia đình hoặc partner.
- Phân quyền xem/sửa theo ví.
- Ghi nhận ai tạo/sửa giao dịch.
- Ẩn số dư hoặc category nhạy cảm.
- Local-first mode.
- Audit log đầy đủ.
- Cấu hình dữ liệu nào được phép gửi sang LLM/provider ngoài.

## 10. Data Safety & Personal Use Requirements

Vì đây là dữ liệu tài chính cá nhân, hệ thống phải ưu tiên an toàn dữ liệu hơn tốc độ tự động hóa.

- Không hard-delete giao dịch; chỉ soft-delete.
- Mọi cập nhật giao dịch phải có audit log.
- Tool sửa/xóa hàng loạt cần xác nhận rõ từ user.
- Dữ liệu tài chính không gửi sang dịch vụ ngoài nếu không cần thiết.
- Export CSV/JSON là requirement bắt buộc trước khi dùng lâu dài.
- Backup database định kỳ.
- Các quyết định mơ hồ phải hỏi lại, không tự đoán để ghi dữ liệu sai.
