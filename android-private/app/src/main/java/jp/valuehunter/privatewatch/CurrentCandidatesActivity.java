package jp.valuehunter.privatewatch;

import android.app.Activity;
import android.app.AlertDialog;
import android.graphics.Color;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.TextView;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/** Current fundamentals-based candidates, not restricted to new alert entrants. */
public final class CurrentCandidatesActivity extends Activity {
    private static final int INK=0xff142336, MUTED=0xff536071, COPPER=0xffa65b36;
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        var root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(0xfffffbf6);
        setContentView(root);
        var title=new TextView(this);title.setText("現在の米国株 割安候補");
        title.setTextColor(Color.WHITE);title.setTextSize(22);title.setPadding(dp(18),dp(17),dp(16),dp(17));
        title.setBackground(new CopperWaveDrawable());root.addView(title);
        var explanation=new TextView(this);explanation.setTextColor(MUTED);explanation.setTextSize(13);
        explanation.setPadding(dp(16),dp(12),dp(16),dp(7));
        explanation.setText("通知がなくても表示。PER・PBRの参考判定と割安メーター3段階は別の指標。表示は保存済みの取引日が基準。");
        root.addView(explanation);
        CurrentCandidates.Snapshot snapshot;
        try {snapshot=CurrentCandidates.load(this);}
        catch(Exception pending){
            var message=new TextView(this);
            message.setText("まだ一覧を表示できない。\n"+pending.getMessage()
                    +"\n\n相場通信を許可し、米国株の財務照合が完了すると表示される。");
            message.setTextColor(INK);message.setTextSize(16);
            message.setPadding(dp(20),dp(25),dp(20),dp(25));
            root.addView(message);
            root.addView(BrandNav.create(this,"相場"));
            return;
        }
        var countLabel=new TextView(this);
        countLabel.setText(snapshot.date()+" 米国取引日  ·  優先候補 "+snapshot.priority()
                +"件  /  参考候補 "+snapshot.reference()+"件");
        countLabel.setTextColor(INK);countLabel.setTextSize(15);
        countLabel.setPadding(dp(16),dp(12),dp(16),dp(8));root.addView(countLabel);
        var search=new EditText(this);
        search.setSingleLine(true);search.setTextSize(15);
        search.setHint("銘柄コード・企業名で検索");
        var searchLayout=new LinearLayout.LayoutParams(-1,dp(52));
        searchLayout.setMargins(dp(14),dp(3),dp(14),dp(7));
        root.addView(search,searchLayout);
        var list=new ListView(this);list.setDividerHeight(dp(1));
        root.addView(list,new LinearLayout.LayoutParams(-1,0,1));
        root.addView(BrandNav.create(this,"相場"));
        var visible=new ArrayList<>(snapshot.rows());
        var adapter=new ArrayAdapter<CurrentCandidates.Row>(this,android.R.layout.simple_list_item_2,
                android.R.id.text1,visible){
            @Override public View getView(int pos,View old,ViewGroup parent){
                View item=super.getView(pos,old,parent);
                var row=getItem(pos);
                TextView top=item.findViewById(android.R.id.text1);
                TextView bottom=item.findViewById(android.R.id.text2);
                top.setText(row.code()+(row.name().isEmpty()?"":"  "+row.name()));
                top.setTextColor(INK);top.setTextSize(16);
                bottom.setText((row.status().equals("priority")?"優先候補":"参考候補")
                        +" · "+row.grade()+" · "+row.quantity()+"株 "+row.purchaseYen()
                        +"円 · PER "+row.per()+" · PBR "+row.pbr());
                bottom.setTextColor(COPPER);bottom.setTextSize(12);
                bottom.setSingleLine(false);
                item.setPadding(dp(14),dp(8),dp(14),dp(8));
                return item;
            }
        };
        list.setAdapter(adapter);
        list.setOnItemClickListener((parent,view,position,id)->{
            var row=adapter.getItem(position);
            new AlertDialog.Builder(this).setTitle(row.code()+(row.name().isEmpty()?"":" · "+row.name()))
                    .setMessage("取引日 "+snapshot.date()+"\n"+row.market()
                            +"\n"+(row.status().equals("priority")?"優先候補":"参考候補")
                            +"（PER・PBR判定）\n割安メーター "+row.grade()
                            +(row.score()>=0?" · "+row.score()+"点":"")
                            +"\n終値 $"+row.closeUsd()+"\n購入 "+row.quantity()+"株 = "
                            +row.purchaseYen()+"円（概算、手数料除外）"
                            +"\nPER "+row.per()+"倍\nPBR "+row.pbr()+"倍"
                            +"\n\n投資判断を保証するものではない。")
                    .setPositiveButton("閉じる",null).show();
        });
        search.addTextChangedListener(new TextWatcher(){
            public void beforeTextChanged(CharSequence s,int start,int count,int after){}
            public void onTextChanged(CharSequence s,int start,int before,int count){
                String query=s.toString().trim().toUpperCase(Locale.ROOT);
                visible.clear();
                for(var row:snapshot.rows()){
                    if(query.isEmpty()||row.code().toUpperCase(Locale.ROOT).contains(query)
                            ||row.name().toUpperCase(Locale.ROOT).contains(query))visible.add(row);
                }
                adapter.notifyDataSetChanged();
                countLabel.setText(snapshot.date()+" · "+visible.size()+"件表示 / "
                        +snapshot.rows().size()+"件  (優先 "+snapshot.priority()
                        +" · 参考 "+snapshot.reference()+")");
            }
            public void afterTextChanged(Editable e){}
        });
    }
}
