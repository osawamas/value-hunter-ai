package jp.valuehunter.privatewatch;
import java.math.BigDecimal;
import java.util.List;
/** Provisional screening model. Missing metrics contribute neither points nor weights. */
final class FlexibleValueMeter {
    static ValueAlertMeter.Score withVerifiedPriorBook(BigDecimal price, List<BigDecimal> eps,
                                                       BigDecimal priorBook) {
        var earnings = assess(price, eps, null, null);
        if (earnings.ceiling() != 1 || priorBook == null || priorBook.signum() <= 0
                || price.compareTo(priorBook.multiply(new BigDecimal("0.5"))) > 0
                || price.compareTo(eps.get(0).multiply(BigDecimal.valueOf(7))) > 0) {
            return earnings;
        }
        // A prior balance sheet corroborates the earnings valuation, but stale book
        // value alone cannot support the highest tier or substitute for current equity.
        return new ValueAlertMeter.Score(earnings.points(), 2, earnings.confirmed() + 1);
    }

    static ValueAlertMeter.Score assess(BigDecimal price,List<BigDecimal> eps,Integer cash,Integer balance) {
        if(price==null || price.signum()<=0 || eps==null || eps.isEmpty() || eps.get(0).signum()<=0)
            return new ValueAlertMeter.Score(0,0,0);
        double pe=price.divide(eps.get(0),java.math.MathContext.DECIMAL64).doubleValue();
        int valuation=pe<=7?100:pe<=10?85:pe<=15?65:0;
        int sum=valuation*50, weight=50, confirmed=1;
        boolean stable=eps.size()>=2 && eps.get(1).signum()>0 &&
            eps.get(0).compareTo(eps.get(1).multiply(new BigDecimal("0.8")))>0;
        boolean loss=eps.stream().anyMatch(x->x.signum()<=0);
        if(eps.size()>=2){sum+=(stable?90:20)*20;weight+=20;confirmed++;}
        if(cash!=null){sum+=cash*20;weight+=20;confirmed++;}
        if(balance!=null){sum+=balance*10;weight+=10;confirmed++;}
        int points=sum/weight;
        if(loss || (eps.size()>=2&&!stable) || Integer.valueOf(0).equals(cash) ||
            Integer.valueOf(0).equals(balance) || valuation==0 || confirmed<2)
            return new ValueAlertMeter.Score(points,0,confirmed);
        int ceiling=1;
        if(stable && cash!=null && cash>=70 && pe<=10) ceiling=2;
        boolean threeYearContinuity = stable && eps.size() >= 3
                && eps.get(1).compareTo(eps.get(2).multiply(new BigDecimal("0.8"))) > 0;
        if (threeYearContinuity && cash != null && cash >= 70
                && balance != null && balance >= 70 && pe <= 7) ceiling = 3;
        return new ValueAlertMeter.Score(points,ceiling,confirmed);
    }
}
