import java.io.\*;

import java.util.\*;



public class Main {

&nbsp;   public static void main(String\[] args) throws Exception {

&nbsp;       BufferedReader br = new BufferedReader(new InputStreamReader(System.in));

&nbsp;       StringBuilder out = new StringBuilder();



&nbsp;       int t = Integer.parseInt(br.readLine());

&nbsp;       while (t-- > 0) {

&nbsp;           String\[] parts = br.readLine().split(" ");

&nbsp;           int n = Integer.parseInt(parts\[0]);

&nbsp;           int L = Integer.parseInt(parts\[1]);

&nbsp;           int R = Integer.parseInt(parts\[2]);



&nbsp;           int\[] A = new int\[n];

&nbsp;           String\[] arr = br.readLine().split(" ");

&nbsp;           for (int i = 0; i < n; i++) {

&nbsp;               A\[i] = Integer.parseInt(arr\[i]);

&nbsp;           }



&nbsp;           Arrays.sort(A);



&nbsp;           long ans = 0;

&nbsp;           int i = 0, j = n - 1;



&nbsp;           while (i < n \&\& j >= 0) {

&nbsp;               int lo = Math.min(R, A\[i]);

&nbsp;               int hi = Math.max(L, A\[j]);



&nbsp;               if (lo >= hi)

&nbsp;                   break;



&nbsp;               ans += (hi - lo);



&nbsp;               i++;

&nbsp;               j--;

&nbsp;           }



&nbsp;           out.append(ans).append('\\n');

&nbsp;       }



&nbsp;       System.out.print(out);

&nbsp;   }

}



