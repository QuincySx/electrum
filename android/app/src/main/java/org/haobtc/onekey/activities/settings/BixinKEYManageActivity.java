package org.haobtc.onekey.activities.settings;

import android.annotation.SuppressLint;
import android.content.Intent;
import android.content.SharedPreferences;
import android.icu.math.BigDecimal;
import android.view.View;
import android.widget.ImageView;

import androidx.recyclerview.widget.RecyclerView;

import com.chad.library.adapter.base.BaseQuickAdapter;
import com.google.common.base.Strings;
import com.google.gson.Gson;

import org.greenrobot.eventbus.EventBus;
import org.greenrobot.eventbus.Subscribe;
import org.greenrobot.eventbus.ThreadMode;
import org.haobtc.onekey.R;
import org.haobtc.onekey.activities.base.BaseActivity;
import org.haobtc.onekey.adapter.BixinkeyManagerAdapter;
import org.haobtc.onekey.aop.SingleClick;
import org.haobtc.onekey.bean.HardwareFeatures;
import org.haobtc.onekey.constant.Constant;
import org.haobtc.onekey.manager.PreferencesManager;
import org.haobtc.onekey.event.FixBixinkeyNameEvent;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import butterknife.BindView;
import butterknife.ButterKnife;
import butterknife.OnClick;

public class BixinKEYManageActivity extends BaseActivity {

    @BindView(R.id.img_back)
    ImageView imgBack;
    @BindView(R.id.recl_bixinKey_list)
    RecyclerView reclBixinKeyList;
    private List<HardwareFeatures> deviceValue;
    private SharedPreferences.Editor edit;

    @Override
    public int getLayoutId() {
        return R.layout.activity_bixin_keymenage;
    }

    @SuppressLint("CommitPrefEdits")
    @Override
    public void initView() {
        ButterKnife.bind(this);
        EventBus.getDefault().register(this);
    }

    @Override
    public void initData() {

    }

    @Override
    protected void onResume() {
        super.onResume();
        getKeylist();
    }

    private void getKeylist() {
        deviceValue = new ArrayList<>();
        Map<String, ?> devicesAll = PreferencesManager.getAll(this, Constant.DEVICES);;
        //key
        for (Map.Entry<String, ?> entry : devicesAll.entrySet()) {
            String mapValue = (String) entry.getValue();
            HardwareFeatures hardwareFeatures = new Gson().fromJson(mapValue, HardwareFeatures.class);
            deviceValue.add(hardwareFeatures);
        }
        if (deviceValue != null) {
            BixinkeyManagerAdapter bixinkeyManagerAdapter = new BixinkeyManagerAdapter(deviceValue);
            reclBixinKeyList.setAdapter(bixinkeyManagerAdapter);
            bixinkeyManagerAdapter.setOnItemChildClickListener(new BaseQuickAdapter.OnItemChildClickListener() {
                @SingleClick
                @Override
                public void onItemChildClick(BaseQuickAdapter adapter, View view, int position) {
                    switch (view.getId()) {
                        case R.id.relativeLayout_bixinkey:
                            String firmwareVersion = "v" + deviceValue.get(position).getMajorVersion() + "." + deviceValue.get(position).getMinorVersion() + "." + deviceValue.get(position).getPatchVersion();
                            String nrfVersion = "v" + deviceValue.get(position).getBleVer();
                            String label = Strings.isNullOrEmpty(deviceValue.get(position).getLabel()) ?
                                    deviceValue.get(position).getBleName(): deviceValue.get(position).getLabel();
                            Intent intent = new Intent(BixinKEYManageActivity.this, HardwareDetailsActivity.class);
                            intent.putExtra(Constant.TAG_LABEL, label);
                            intent.putExtra(Constant.TAG_BLE_NAME, deviceValue.get(position).getBleName());
                            intent.putExtra(Constant.TAG_FIRMWARE_VERSION, firmwareVersion);
                            intent.putExtra(Constant.TAG_NRF_VERSION, nrfVersion);
                            intent.putExtra(Constant.DEVICE_ID, deviceValue.get(position).getDeviceId());
                            intent.putExtra(Constant.AUTO_SHUT_DOWN_TIME, deviceValue.get(position).getAutoLock().divide(new BigInteger(String.valueOf(1000))).toString());
                            startActivity(intent);
                            break;
                        case R.id.linear_delete:
//                            String deviceId = deviceValue.get(position).getDeviceId();
//                            edit.remove(deviceId).apply();
//                            deviceValue.remove(position);
//                            bixinkeyManagerAdapter.notifyItemChanged(position);
//                            bixinkeyManagerAdapter.notifyDataSetChanged();
//                            mToast(getString(R.string.delete_succse));
                            break;
                        default:
                    }
                }
            });
        }
    }

    @SingleClick
    @OnClick({R.id.img_back})
    public void onViewClicked(View view) {
        if (view.getId() == R.id.img_back) {
            finish();
        }
    }

    @Subscribe(threadMode = ThreadMode.MAIN)
    public void showReading(FixBixinkeyNameEvent event) {
        getKeylist();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        EventBus.getDefault().unregister(this);
    }
}






