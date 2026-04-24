import { Nav, PageFooter } from "./Nav";
import { navigate } from "../router";
import { AdSlot } from "../components/AdSlot";

export function HowItWorks() {
  return (
    <div className="app site-page">
      <Nav current="/how-it-works" />
      <main className="content-page">
        <header className="content-hero">
          <h1>予測ロジックの仕組み</h1>
          <p>
            FIGHT PREDICTが「どうやって勝敗を予測しているのか」を、
            データソース・スコアリング項目・機械学習モデルまで含めて全て公開しています。
            ブラックボックスではなく、再現可能なロジックで動いているツールです。
          </p>
        </header>

        <section className="content-block">
          <h2>1. 何をしているツールか</h2>
          <p>
            FIGHT PREDICTは、UFC（Ultimate Fighting Championship）とRIZIN（日本の総合格闘技団体）の
            任意の2選手について、公開されているスタッツと戦績データを自動収集し、
            両者の勝敗確率と信頼度を算出するAIツールです。単に「有名選手が勝つ」「連勝中だから勝つ」
            という一面的な判定ではなく、17項目のスコアリングと機械学習モデルを組み合わせて、
            データに基づいた確率を出すことを目的としています。
          </p>
          <p>
            予測の出力は次の4つです。
          </p>
          <ul>
            <li>選手A/Bの勝率（%）</li>
            <li>予想される決着方法（KO/TKO・Submission・Decision）</li>
            <li>信頼度（HIGH / MEDIUM / LOW）</li>
            <li>主要な判断根拠（勝率差・年齢差・スタイル相性など）</li>
          </ul>
        </section>

        <section className="content-block">
          <h2>2. データソース</h2>
          <p>
            すべての予測は、以下の公開サイトからスクレイピングで取得したデータに基づいています。
            独自の主観的な重みづけや、非公開データは一切使用していません。
          </p>
          <ul>
            <li>
              <strong>UFC選手データ</strong>：UFCstats.com
              （全UFC選手の戦績・打撃・TD・サブミッション関連の公式スタッツ）
            </li>
            <li>
              <strong>RIZIN選手データ</strong>：Sherdog.com
              （RIZIN全80大会の出場選手データを自動収集）
            </li>
            <li>
              <strong>過去の対戦履歴</strong>：UFCstats.com および Sherdog.com の個人ページから全試合を抽出
            </li>
          </ul>
          <p>
            RIZIN選手はUFCほど詳細なスタッツが公式に公開されていないため、
            戦績（勝ち方の内訳・連勝連敗）から打撃・TD・サブミッションの傾向を推定するロジックを用いています。
            推定データを使用した予測は、その旨を予測根拠欄に明示します（「※スタッツは戦績から推定」）。
          </p>
        </section>

        <section className="content-block">
          <h2>3. 17項目スコアリングの内訳</h2>
          <p>
            両選手を17項目で比較し、それぞれの項目に設定された重みに従ってスコアを積み上げます。
            最後にシグモイド関数で確率に変換することで、両選手の勝率の合計が必ず100%になるよう正規化しています。
          </p>

          <h3>A. 戦績・実績系（重み合計 約40%）</h3>
          <ul>
            <li>
              <strong>勝率</strong>：全試合のW/(W+L+D)。総試合数が多いほど信頼度への寄与も大きくなる
            </li>
            <li>
              <strong>直近5試合の調子</strong>：連勝中か連敗中か、直近で失速していないか
            </li>
            <li>
              <strong>KO/TKO勝率</strong>：フィニッシュ力の指標。Decisionに頼っていないか
            </li>
            <li>
              <strong>サブミッション勝率</strong>：グラップリング完結力
            </li>
            <li>
              <strong>判定勝率</strong>：僅差で勝ち切れるか（タフネス・スタミナの代理指標）
            </li>
            <li>
              <strong>対戦相手の質（Strength of Schedule、重み約6%）</strong>
              ：過去に戦った相手の平均勝率。強豪揃いの相手を勝ち抜いている選手は高評価
            </li>
          </ul>

          <h3>B. 打撃・グラップリング系（重み合計 約30%）</h3>
          <ul>
            <li>
              <strong>有効打（SigStr/分）</strong>：1分間あたりに当てた有効打撃数
            </li>
            <li>
              <strong>被弾率</strong>：1分間あたりに受けた有効打撃数（少ないほど評価が高い）
            </li>
            <li>
              <strong>打撃防御率</strong>：相手の打撃を防いだ割合
            </li>
            <li>
              <strong>テイクダウン/試合</strong>：レスリング能力の核
            </li>
            <li>
              <strong>テイクダウン防御率</strong>：寝技に持ち込まれない能力
            </li>
            <li>
              <strong>サブミッション試行率</strong>：寝技での決着力
            </li>
            <li>
              <strong>スタイルマッチアップ</strong>：ストライカー vs グラップラーの相性評価。
              例えば「打撃主体 vs TD防御の低いレスラー嫌い」のような構造を検出する
            </li>
          </ul>

          <h3>C. フィジカル・コンディション系（重み合計 約20%）</h3>
          <ul>
            <li>
              <strong>リーチ差</strong>：ストライカー同士ほど効く
            </li>
            <li>
              <strong>年齢・キャリアフェーズ</strong>：25〜32歳をピークとし、36歳以上は段階的にペナルティ。
              DOB（生年月日）から現在の年齢を自動算出
            </li>
            <li>
              <strong>ブランク（レイオフ）</strong>：最終試合日からの経過月数。
              12ヶ月以上のブランクはコンディション面でマイナス評価
            </li>
            <li>
              <strong>階級変更</strong>：直前に階級を上下しているかの補正
            </li>
          </ul>

          <h3>D. 対戦特化系（重み合計 約10%）</h3>
          <ul>
            <li>
              <strong>直接対決（Head-to-Head）</strong>：過去の対戦がある場合のその結果
            </li>
          </ul>
        </section>

        <section className="content-block">
          <h2>4. 機械学習モデル（ロジスティック回帰）</h2>
          <p>
            17項目のルールベーススコアに加え、Sherdog UFCオーガナイゼーションページから
            直近5大会の過去試合結果を自動スクレイピングして学習させた
            ロジスティック回帰モデル（scikit-learn + numpy）を併用しています。
          </p>
          <p>
            入力特徴量は12次元：
          </p>
          <ul>
            <li>勝率の差、打撃/分の差、打撃防御率の差、被弾率の差</li>
            <li>テイクダウン/試合の差、テイクダウン防御率の差、サブミッション試行率の差</li>
            <li>リーチ差、年齢差</li>
            <li>直近5試合の連勝数、フィニッシュ率、総試合数</li>
          </ul>
          <p>
            学習時は左右を入れ替えたデータを混ぜることで、
            「入力順が勝敗に影響する」クラス不均衡バイアスを排除しています。
            モデルはリポジトリに保存されており、サーバー起動時にロードされます
            （保存モデルがあれば再学習はスキップ）。
          </p>
        </section>

        <section className="content-block">
          <h2>5. ルールベースとMLのブレンド予測</h2>
          <p>
            最終的な勝率は、17項目ルールベーススコア（ウェイト60%）と
            機械学習モデル（ウェイト40%）の加重平均で算出します。
          </p>
          <p>
            なぜブレンドするのか。ルールベーススコアは、どの項目がどう寄与したかを人間が解釈しやすい反面、
            重みの設計に主観が入りやすい。一方、機械学習モデルは純粋なデータ駆動で客観的ですが、
            学習データに偏りがあると判断を誤ります。両者を組み合わせることで、
            解釈性と予測精度の両立を図っています。
          </p>
          <p>
            なお、推定データのみを使っている選手（主にRIZINのスタッツ非公開選手）については、
            ML予測の信頼性が下がるため自動的にスキップし、ルールベースのみで判定します。
            この場合、予測根拠に「※スタッツは戦績から推定」と明示されます。
          </p>
        </section>

        <section className="content-block">
          <h2>6. 信頼度（HIGH / MEDIUM / LOW）の判定</h2>
          <p>
            勝率の数字だけでは、「52% vs 48%の接戦」と「85% vs 15%の大差」を同列に扱ってしまいます。
            そこでFIGHT PREDICTは、勝率とは別に信頼度を独立で出力します。
          </p>
          <ul>
            <li>
              <strong>HIGH</strong>：勝率差が大きく、かつ両選手のデータ量が十分で、
              推定データを含まない場合
            </li>
            <li>
              <strong>MEDIUM</strong>：勝率差が中程度、またはどちらかの選手のデータが限定的な場合
            </li>
            <li>
              <strong>LOW</strong>：勝率差が僅差、データ不足、推定データが多い、
              新人同士などの場合
            </li>
          </ul>
          <p>
            信頼度判定には、選手AとBそれぞれについて「試合数が十分か」「直近試合データがあるか」
            「推定データではないか」「対戦相手の質データがあるか」の4軸のデータ品質スコアを使います。
          </p>
        </section>

        <section className="content-block">
          <h2>7. 限界と注意点</h2>
          <p>
            このツールは過去データから確率を出す統計予測であり、試合結果を保証するものではありません。
            特に以下の要素はスコアに含まれていません。
          </p>
          <ul>
            <li>当日の体重オーバー・コンディション不良</li>
            <li>怪我・メンタル状態・陣営の変化（コーチ変更、ジム移籍）</li>
            <li>メディアやネット上の噂・選手の発言</li>
            <li>会場の雰囲気やレフェリーの傾向</li>
          </ul>
          <p>
            また、格闘技はラウンド中の一瞬の打撃やサブミッションで結果が大きく変わる競技であり、
            予測確率85%のカードが外れることも普通にあります。
            あくまで「データだけを見たらどちらに優位性があるか」の参考値としてご利用ください。
          </p>
        </section>

        <AdSlot placement="content-bottom" />

        <section className="content-block">
          <h2>8. 的中率の公開</h2>
          <p>
            予測精度の検証のため、過去の予測結果を全てJSON形式でサーバー側に保存し、
            「的中率」タブから誰でも閲覧できるようにしています。信頼度HIGH/MEDIUM/LOWごとの的中率内訳も公開中で、
            「HIGHのときは本当に当たるのか」「LOWはどれくらい外れるのか」を透明に公開しています。
            予測を信じるかどうかの判断材料としてお使いください。
          </p>
          <button
            className="article-cta-btn"
            onClick={() => navigate("/")}
          >
            予測ツールを試す
          </button>
          <button
            className="article-cta-btn secondary"
            onClick={() => navigate("/faq")}
          >
            よくある質問を見る
          </button>
        </section>
      </main>
      <PageFooter />
    </div>
  );
}
