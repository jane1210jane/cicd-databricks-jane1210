# GitHub Free → Databricks Free Edition CI/CD

確認日: 2026-11-12（日本時間）

GitHub ActionsでPythonをテストし、`main`更新時にDatabricksへノートブックとJobをデプロイして、実行結果まで確認する学習用サンプルです。

**認証の前提: 利用するFree EditionワークスペースでDatabricksの個人アクセストークン（PAT）を発行・使用できること。** CLI/BundlesのFree Edition対応はDatabricks公式サンプルにあります。一方、すべてのFree EditionアカウントでPATを発行できるという公式の保証までは確認できていません。最初に以下のPAT設定画面を確認してください。[公式サンプル](https://github.com/databricks-solutions/caspers) / [公式PAT設定](https://docs.databricks.com/aws/en/dev-tools/auth/pat)

Free Editionは非商用の学習・実験向けで、サーバーレスのみ、使用量制限あり、SLAなしです。この構成は業務用本番運用の提案ではありません。[公式制限](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)

## 1. 何が動くか

| 操作 | GitHub側 | Databricks側 |
| --- | --- | --- |
| `main`向けPull Request | 単体テスト、Python構文確認 | 接続しません |
| `main`へのpush・PRマージ | テスト成功後にデプロイ処理 | ノートブックとJobを更新し、1回実行して結果を確認 |
| Actionsから手動実行、ブランチ=`main` | 同じ処理 | 同じ処理 |
| 別ブランチから手動実行 | テストのみ | 接続しません |

デプロイにはDatabricks Bundlesを使います。現在の公式名称は **Declarative Automation Bundles**、旧称は **Databricks Asset Bundles** です。コードとJob設定をYAMLで管理し、CLIから配布します。[公式説明](https://docs.databricks.com/aws/en/dev-tools/bundles/settings)

サンプルは架空の売上データを商品別に集計し、専用のDeltaテーブル `workspace.github_cicd_demo.sales_summary` へ保存します。テーブルを読み直し、apple=360円、banana=240円でなければJobを失敗させます。**このサンプルテーブルは実行のたびに上書きされます。**

## 2. ファイル

次のファイルをGitHubリポジトリのルートに配置します。ZIPの外側のフォルダー名ではなく、中身をルートへ置いてください。`.github`と`.gitignore`も必要です。

| ファイル | 役割 |
| --- | --- |
| `.github/workflows/databricks-cicd.yml` | テスト・認証・Bundle検証・デプロイ・実行 |
| `databricks.yml` | ノートブックJob、配布先、カタログ設定 |
| `src/etl_notebook.py` | Databricksで実行するノートブック |
| `src/transforms.py` | GitHubとDatabricksで共用する集計関数 |
| `tests/test_transforms.py` | 集計結果の単体テスト3件 |
| `.gitignore` | トークン設定ファイル、ローカル生成物等の除外 |
| `README.md` | この導入手順 |

実装上の選択は、Python 3.12、GitHub標準Linuxランナー `ubuntu-24.04`、Databricks CLI 1.26.0です。Actionは確認できた固定版を指定しています。CLIを更新するときはWorkflowの`uses`・`with.version`と`databricks.yml`の`databricks_cli_version`をそろえて変更します。[CLI公式リリース](https://github.com/databricks/cli/releases/tag/v1.26.0) / [setup-cli公式説明](https://github.com/databricks/setup-cli)

## 3. 初回設定

### 3-1. DatabricksのホストURLとPAT

1. Databricks Free Editionのワークスペースを開きます。
2. ブラウザーのURLからホスト部分を控えます。例: `https://dbc-xxxxxxxx-xxxx.cloud.databricks.com`。`/editor/...`や`?o=...`は含めません。`https://accounts.cloud.databricks.com`ではありません。
3. ユーザーメニュー → **Settings → Developer → Access tokens → Manage → Generate new token** を開きます。
4. 例えば名前を`github-actions-demo`、有効期限を30日にして、個人PATを発行します。
5. 発行された値を控え、次のGitHub Secretsへ登録します。

APIスコープを選ぶ画面がある場合は **Other APIs** を使います。APIの対応では `jobs`（Job作成・実行）と `workspace`（Workspaceへの配布）が基本です。Bundleの権限API操作も許可する場合は `access-management` を追加します。`current-user me`は任意の有効なscoped tokenで呼べるため、そのためだけの`scim`追加は不要です。CLI全処理を通した最小スコープの実機確認は未実施です。SQL/BI専用トークンではこのサンプルは動きません。[API scopes](https://docs.databricks.com/api/workspace/scopes) / [current-user API](https://docs.databricks.com/api/scim/v1/me)

PATのスコープはユーザー自身の権限を増やすものではありません。なお、APIからPATを発行する場合、全APIアクセスの指定は`"scopes": []`であり、`"all-apis"`という文字列を渡す指定ではありません。このサンプル自体はトークン発行APIを呼びません。[公式PAT設定](https://docs.databricks.com/aws/en/dev-tools/auth/pat)

これは**DatabricksのPAT**です。GitHubで発行するPATとは別のものです。トークンをコード、Issue、チャットには貼らず、期限切れ前にGitHub Secretを更新してください。

Access tokensが表示されない、または発行を拒否される場合、このPAT版の自動CDはそのままでは動きません。ワークスペースの設定・権限を確認してください。サービスプリンシパルとOAuth secretを利用できる環境ならOAuth M2M方式へ変更する余地がありますが、Free Edition全体での可否はここでは保証しません。対話が必要な`databricks auth login`をGitHubの無人ランナーにそのまま置く方法にはしません。[OAuth M2M公式設定](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-m2m)

### 3-2. GitHubのRepository secrets

リポジトリの **Settings → Secrets and variables → Actions → Secrets → New repository secret** で次の2件を登録します。[公式手順](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)

| 名前 | 値 |
| --- | --- |
| `DATABRICKS_HOST` | 3-1のワークスペースホストURL |
| `DATABRICKS_TOKEN` | 3-1で発行したDatabricks PAT |

GitHub Freeの非公開リポジトリでも使うため、Environment secretsではなく、**Repository secrets**を使います。Workflowに`environment: production`等は不要です。Freeの非公開リポジトリではEnvironmentsが利用できません。[公式のプラン制限](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)

### 3-3. カタログの確認

DatabricksのCatalog画面で、既存の`workspace`カタログがあるか確認します。実行ユーザーにそのカタログの利用とスキーマ作成の権限が必要です。

別名のカタログを使う場合は、GitHubの同じActions設定画面の **Variables → New repository variable** で次を追加します。

| 名前 | 値 |
| --- | --- |
| `DATABRICKS_CATALOG` | 実際に存在して書き込み可能なカタログ名 |

未設定なら`workspace`です。`github_cicd_demo`スキーマと`sales_summary`テーブルはノートブックが作成します。外部ストレージ、DBFS mount、クラウドのアクセスキーは使いません。

### 3-4. ファイルをpush

既存のリポジトリへ入れる場合は通常の作業ブランチで追加し、PRからmainへ反映します。

空の新規GitHubリポジトリへ配置する場合は、ZIPを展開したフォルダーで次を実行できます。`YOUR_GITHUB_USER`とリポジトリ名を実際の値へ置き換えてください。GitHubへのGit認証は事前に設定します。

```bash
git init -b main
git add .
git commit -m "Add Databricks Free Edition CI/CD demo"
git remote add origin https://github.com/YOUR_GITHUB_USER/databricks-free-cicd.git
git push -u origin main
```

リポジトリの既定ブランチは`main`とします。Actionsが無効になっている場合はリポジトリ設定で有効にします。別の既定ブランチ名を使うなら、Workflowのtrigger、deployの`if`、`Require current main commit`のAPIパスとメッセージも変更します。

初回push時にSecretsが未登録だった場合は、Secrets登録後にActionsから **Run workflow → main** を実行します。GitHub側に追加のPATを登録する必要はありません。mainのコミット確認に使う`github.token`はGitHub Actionsが発行するトークンです。

## 4. 成功の確認

GitHubのActionsで次の順に成功することを確認します。

1. `test`: 単体テスト3件、Python構文確認。
2. `deploy`: mainのコミット確認、Databricks認証、`bundle validate`。
3. `bundle deploy`: ノートブック・共有Pythonファイル・Jobの作成または更新。
4. `bundle run`: Jobの完了まで待ち、書き込んだテーブルの内容を確認。

DatabricksのJobs画面には`github-free-edition-demo`が作成されます。実行履歴で`run_demo`タスクを開くと結果を確認できます。

SQLで確認する場合:

```sql
SELECT product, total_yen
FROM workspace.github_cicd_demo.sales_summary
ORDER BY product;
```

| product | total_yen |
| --- | ---: |
| apple | 360 |
| banana | 240 |

カタログ名を変更した場合はSQLの`workspace`も変更します。ローカルでテストだけ行う場合は、Python 3.12で次を実行します。追加のPythonライブラリは不要です。

```bash
python -m unittest discover -s tests -v
python -m compileall -q src
```

ノートブックを通常のPythonで直接実行することはできません。`spark`、`dbutils`、`display`はDatabricks環境から提供されます。サーバーレスの作業ディレクトリは保証されないため、Jobの`source_dir`引数にBundleが解決した絶対パスを渡して共有モジュールを読み込みます。[公式サーバーレス制限](https://docs.databricks.com/aws/en/compute/serverless/limitations)

## 5. 設計上のポイント

- **クラスターIDは不要です。** Notebook taskでcluster設定を省くサーバーレスJobの公式構成を使います。`existing_cluster_id`や`new_cluster`を追加しないでください。[公式Bundle例](https://docs.databricks.com/aws/en/dev-tools/bundles/examples)
- GitHub側の`needs: test`により、その実行のテストが失敗したらデプロイしません。mainに直接pushした場合も同じです。
- 通常のPRテストにはDatabricks Secretsを渡しません。リポジトリ書き込み権限を持つ人はWorkflowを変更できるため、共同編集者は信頼できる人に限定します。
- 同時デプロイを避け、実行中のデプロイを新しいpushでキャンセルしません。古いWorkflowの再実行で新しいmainを上書きしないよう、開始時にコミットを確認します。全コミットのデプロイを保証するキューではありません。
- 実行中のJobがある場合、`--fail-on-active-runs`でデプロイを止めます。Databricks画面から手動起動したJobにも注意してください。
- `bundle.name`、target名、配布先`root_path`と認証ユーザーをそろえることで、同じ配布先のJobを更新します。別のリポジトリでもこのサンプルを使う場合は、bundle名・Job名・出力先テーブルをそれぞれ変更してください。[Bundleの識別と状態管理](https://docs.databricks.com/aws/en/dev-tools/cli/bundle-commands)
- CLIの`bundle run`にはこの版で`--timeout`引数がありません。GitHub stepの15分制限とDatabricks Jobの600秒制限を設定しています。GitHubの中断とDatabricks上の停止が完全に同時になるとは限りません。
- Job実行失敗時はActionsを失敗にしますが、すでに配布したコードを自動では戻しません。戻す場合は必要なコミットをrevertしてmainへ反映し、再デプロイします。出力テーブルの更新も自動では取り消されません。

`git_source`でDatabricksからGitHubをpullする方式ではなく、GitHub ActionsがcheckoutしたファイルをBundleで配布する方式です。そのため、この構成のためだけにDatabricks側のGitHub連携を登録する必要はありません。

## 6. 無料枠

2026-11-12に確認した公式資料では次の扱いです。

| 対象 | 無料枠・制限 |
| --- | --- |
| GitHubの公開リポジトリ | 標準GitHub-hosted runnerは無料 |
| GitHub Freeの非公開リポジトリ | 月12 USD相当のcompute枠。Linux 2-core x64の単価0.006 USD/分だけなら約2,000分相当。他の対象利用と共有 |
| GitHub Artifact storage | 500 MB。今回のWorkflowはArtifactのアップロードやcacheを使用しません |
| Databricks Free Edition | サーバーレスのみ。アカウント全体で同時Job task最大5。使用量超過時は当日中、場合によっては月内のcompute利用が停止 |

GitHubでJob完了を待っている間もrunnerの使用量を消費します。追加課金を避けたい場合はBillingで予算到達時の使用停止を有効にし、無料枠を確認してください。

根拠: [GitHub無料枠](https://docs.github.com/en/billing/reference/product-usage-included) / [runner単価](https://docs.github.com/en/billing/reference/actions-runner-pricing) / [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) / [Databricks Free Edition制限](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)

## 7. よくあるエラー

| 状況 | 確認すること |
| --- | --- |
| `DATABRICKS_HOST` / `DATABRICKS_TOKEN`未設定 | Repository secretsに名前を正確に登録したか |
| 認証エラー・401 | Databricks PATか、有効期限内か、発行したworkspaceとhostが一致するか |
| 403・権限エラー | ユーザー権限、PATのスコープ、Jobs/Workspaceへの操作権限 |
| カタログが見つからない | Catalog画面で実際の名前を確認し`DATABRICKS_CATALOG`へ設定 |
| スキーマ・テーブル作成が拒否される | カタログ利用・スキーマ作成・テーブル作成の権限 |
| `ModuleNotFoundError: transforms` | `src/transforms.py`がGit管理され、Jobの`source_dir`が最新のBundle設定で配布されているか |
| `source_dir`が空 | このノートブックをBundleで作成したJobとして実行しているか |
| クラスター作成・未対応compute関連 | `new_cluster`等を追加していないか |
| quota・使用量超過 | Databricksの使用量制限が解除されてから最新mainを再実行 |
| running jobs/pipelinesによりdeploy失敗 | 実行終了を待ってから再実行 |
| `no longer the current main commit` | 最新mainのWorkflowを実行。古い版へ戻すならrevertをmainへ反映 |
| 同時実行による待機 | 他のデプロイが完了するまで待つ。ロックを強制解除しない |

## 8. 検証範囲

作成時に単体テスト3件、Python・YAML・シェル構文、Databricks CLI v1.26.0の実際のhelpに基づく引数、同CLI生成のJSON Schemaに対するBundle設定の検証を行っています。

**GitHub Actions上の実行、PATによる実ワークスペースへの認証、DatabricksでのJob実行は未検証です。** 利用者のリポジトリ・ワークスペース・認証情報が未指定のため、これらが成功したとは扱っていません。認証後の`bundle validate`はWorkflow自身が行います。
