import streamlit as st


# 数値入力欄（st.number_input）の視認性を整えるスタイル。
#
# Streamlit 標準の number_input は「Press Enter to submit form」案内を
# 入力欄へ position:absolute で重ねて描画するため、列幅が狭い修正画面では
# 入力中の数値に案内が被って読めなくなる。案内の非表示は number_input 配下に
# 限定し、メモ・食事ログなどのテキスト入力では従来どおり表示させる。
#
# streamlit 1.40.2 の number_input は
#   <div class="stNumberInput" data-testid="stNumberInput"> … </div>
# を出力し、案内は配下の data-testid="InputInstructions" に描画される。
# 将来どちらの名称が変わっても効き続けるよう両方を併記している。
# 万一どちらも効かなくなっても案内が再表示されるだけで、
# 入力・＋／－・Enter 送信・保存の動作は影響を受けない。
# ステップボタン（stNumberInputStepUp / StepDown）には手を入れない。
_NUMBER_INPUT_STYLE = """
<style>
/* 「Press Enter to submit form」案内を数値入力欄でのみ隠す */
[data-testid="stNumberInput"] [data-testid="InputInstructions"],
.stNumberInput [data-testid="InputInstructions"] {
    display: none !important;
}

/* 入力値は通常時もフォーカス時も明るい文字色を保つ */
[data-testid="stNumberInput"] input,
[data-testid="stNumberInput"] input:focus,
.stNumberInput input,
.stNumberInput input:focus {
    color: #FAFAFA !important;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

/* 未入力時のプレースホルダーは入力値より暗くして区別する */
[data-testid="stNumberInput"] input::placeholder,
.stNumberInput input::placeholder {
    color: rgba(250, 250, 250, 0.55) !important;
    font-weight: 400;
}
</style>
"""


def inject_number_input_styles() -> None:
    """Inject the constant number input readability stylesheet.

    Called once per page render from streamlit_app.py. The stylesheet is a
    module-level constant; never interpolate values into it.
    """
    st.html(_NUMBER_INPUT_STYLE)
