package org.haobtc.wallet.activities;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.text.InputType;
import android.text.TextUtils;
import android.view.MotionEvent;
import android.view.View;
import android.view.inputmethod.InputMethodManager;

import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import com.chaquo.python.PyObject;

import org.haobtc.wallet.R;
import org.haobtc.wallet.activities.base.BaseActivity;
import org.haobtc.wallet.utils.Global;
import org.haobtc.wallet.utils.NfcUtils;
import org.haobtc.wallet.utils.NumKeyboardUtil;
import org.haobtc.wallet.utils.PasswordInputView;

import java.util.Objects;

import butterknife.BindView;
import butterknife.ButterKnife;
import butterknife.OnClick;

public class PinSettingActivity extends BaseActivity {
    @BindView(R.id.trader_pwd_set_pwd_edittext)
    PasswordInputView edtPwd;
    @BindView(R.id.img_back)
    ImageView imgBack;
    @BindView(R.id.bn_next)
    Button bnCreateWallet;
    @BindView(R.id.pin_description)
    TextView textViewPinDescription;
    private NumKeyboardUtil keyboardUtil;
    // old version code todo: remove
    private String tag;

    @Override
    public int getLayoutId() {
        return R.layout.pin_input;
    }

    public void initView() {
        ButterKnife.bind(this);
        edtPwd.setInputType(InputType.TYPE_NULL);
        keyboardUtil = new NumKeyboardUtil(this, this, edtPwd);
        // old version code todo:remove
        /*tag = getIntent().getStringExtra(TouchHardwareActivity.FROM);
        if (CoSignerAddActivity.TAG.equals(tag) || TransactionDetailsActivity.TAG.equals(tag)) {
            textViewPinDescription.setText(getResources().getString(R.string.pin_input));
        }*/

        // new version code todo:open
        int tag = getIntent().getIntExtra("pin", 0);
        switch (tag) {
            case 1:
                textViewPinDescription.setText(getString(R.string.pin_input));
                break;
            case 2:
                textViewPinDescription.setText(getString(R.string.set_PIN));
                break;
            default:

        }
        init();
    }

    @Override
    public void initData() {

    }

    @SuppressLint("ClickableViewAccessibility")
    private void init() {
        edtPwd.setOnTouchListener((v, event) -> {
            keyboardUtil.showKeyboard();
            return false;
        });

        edtPwd.setOnFocusChangeListener((v, hasFocus) -> {
            if (hasFocus) {
                // If the system keyboard is in pop-up state, hide it first
                try {
                    ((InputMethodManager) Objects.requireNonNull(getSystemService(INPUT_METHOD_SERVICE)))
                            .hideSoftInputFromWindow(Objects.requireNonNull(getCurrentFocus())
                                            .getWindowToken(),
                                    InputMethodManager.HIDE_NOT_ALWAYS);
                } catch (Exception e) {
                    e.printStackTrace();
                } finally {
                    keyboardUtil.showKeyboard();
                }
            } else {
                keyboardUtil.hideKeyboard();
            }
        });

    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        if (event.getAction() == MotionEvent.ACTION_DOWN) {
            if (getCurrentFocus() != null && getCurrentFocus().getWindowToken() != null) {
                keyboardUtil.hideKeyboard();
            }
        }
        return super.onTouchEvent(event);
    }


    @OnClick({R.id.img_back, R.id.bn_next})
    public void onViewClicked(View view) {
        switch (view.getId()) {
            case R.id.img_back:
                finish();
                break;
            case R.id.bn_next:
                if (edtPwd.getText().length() == 6) {
                    // old version code todo:remove
                    // startNewPage(tag);

                    // new version code todo: open
                    Intent intent = new Intent();
                    intent.putExtra("pin", edtPwd.getText().toString());
                    setResult(Activity.RESULT_OK, intent);
                    finish();
                } else {
                    Toast.makeText(getBaseContext(), "the PIN's length less than 6", Toast.LENGTH_SHORT).show();
                }
                break;
        }
    }

    private void startNewPage(String tags) {
        if (!TextUtils.isEmpty(tags) && !NfcUtils.mNfcAdapter.isEnabled()) {
            PyObject ui = Global.py.getModule("trezorlib.customer_ui");
            PyObject customerUI = ui.get("CustomerUI");
            customerUI.put("pin", edtPwd.getText().toString());
        }
        switch (tags) {
            case WalletUnActivatedActivity.TAG:
                Intent intent = new Intent(this, ActivatedProcessing.class);
                intent.putExtra("pin", edtPwd.getText().toString());
                startActivity(intent);
                break;
            case CoSignerAddActivity.TAG:
                Intent intent1 = new Intent();
                intent1.putExtra("pin", edtPwd.getText().toString());
                setResult(1, intent1);
                finish();
                break;
            case TransactionDetailsActivity.TAG:
                Intent intent2 = new Intent();
                intent2.putExtra("pin", edtPwd.getText().toString());
                intent2.putExtra(TouchHardwareActivity.FROM, TransactionDetailsActivity.TAG);
                setResult(1, intent2);
                finish();
                break;
            default:
        }
    }

    @Override
    protected void onRestart() {
        super.onRestart();
        // old version code todo: remove
        //finish();
    }
}
