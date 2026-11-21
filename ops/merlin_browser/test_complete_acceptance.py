"""Fixed-controller controls; simulated host/transport cases are labelled.

The retained receipt fixture is exact original native evidence. Native helper
calls in orchestration tests are explicitly mocked; no browser or host change
is performed by this test module.
"""
import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zlib

import complete_acceptance as C

# Generated only from the preserved run44946846703 files and installed manifest.
FIXTURE = 'c-rlKX_FL3vh80f!|Xl@GrBwWMOc535E}7D0-ivoH&@8YVr^<vT~)Uh5HpYe{*LETTUSHVEMjI_3v_2jMtXX996#<E>G987&!>y!t*>tV^VzL9pT1m_`S5I%pWXV(J9cMtY_)Z){87?s8REF$(6d`7tHu0eJc>r0r04VL`Dk^1)LnM+yo5Y1i^Xv9yo|@sZtYx+gF$H1bRvYaOj;F96(QBYSV%T$6__tkvJg__DTm~x2r+nDj8;YFT9tN^yV`U;FXIvxomA7=^5neC$D_&7Y!%0&v=*vswm8wQ`lxCtE;5;;wKgzYtl`R+s%yz9xx|x?QZk>oQ64|0kV~o&qOkU+tI2Y7UWVskGOA^<+<q#}lW|d3n@Z#?ml%a*wdP!eV%{j{jm!9l^P-EFNmlQmW0BB9blEjGSfuCWJT(1v&(l4~5e?l5e|GEjv&pSHw<hJ~T8LX;{qt5X^U;g298D+mTY4TQXC)73;njE=^5WK4zuua?T0WmnIxU^FS{inpAJ1N)&#uK1T`rnGhZkG@cIVdbqe+Gh&C6oCnx}FUQks%lCTB;p`82N*gbkB?G%sgpvw%oPi&aYaaXP2Fgn5}P_ce$POVIdF@XE9nR;FyS6UhY(MK#58$*sU(upBjy&}vPd>mapqwenKUrtf}~)?Mr9jg3Yc6`^S<IJB>A;mRc?8SaH44^ipNrIfA~Z7qJ(Mpu_v@flsOA7R)&<Z_s%=jS7uO)%ulJU6D|VhCAPsM5ilxloCVs3Wt?@o?+)9ZZN>nd6}w)or?PMO2=RmzHM@E4793B4f-t1SWzp28N><J!2hVj$uImc`LqJ(oaHpCGOlh8!d-%JdNm0X<ky$PDELa4m>K@Z?w{Q7@{;%7@vf-0=-S=qq9+CGZDjzF{FX`Bc$a3{SBzUyMrl2ZcJ<NaytLLj;AjNt>A-sNz-{Qd4Oxntl*Eya@?3wSUyKj)7hdkxZZ|N#$h!{&xd6;T1<0k4R2m%)5T~xoxj30=hOLFn1sb_bbfL#kbTW&q`9t3h}rdV)b&Aw(+{+)unh%8)tIbeg8Lk*#q(={$ypqaB}fsW-e9e^&N=NkDcyN*fC9MDTCa{Xx1&}cvv&%H!d0v>D<un_9j&Tx%qEkZwi%=LXQ*{?KK;E6=hSxI&*yhl>!Ci@nhicB86swpElFt3gDqK`C_+`3r#>j5LYBbtDqvxS6=zr~IVbI5+<sfLoXH)<S_cC+9y3!`j=3V8!?YG&0SHX?l8213N^D25*O@!r!*)QIr^{g&4X2Bf;czs8IKu;a`!P%=ub{R0^rW4;NAqc%F1J+omfkiX6tv24d8Cra1IH6tm?IR&oG-=em`iZnS+1cumw-mq85cz4rYL8(H7F$GyE+tA0J1WZF!RI;=D!C70UuqpnEpal2b1;nqv<ftNBOLL7!7Xswbq|?Tqzsjj=j-^^C*3Wugx{_tROwSwMoWS%|xs<8Mt@DG^Rg%hJzw@^k?;s_83f8S1p+3HF7O&;^-oJ?t%{%ej+Lkfaf1rdz~}>5axHVtF`Vh@Iuxae00*~!VKK2b43M%>83IV6RBF)DnkHgDWYVj8F&&vF@QJi>Q3*un-F9w#(+UNK{MIG0Wuz7gu2M8lHs6uHOr5qyf9ymDv%YxRX>0NFLt+9BBo}Mz<d>=DZoEpm{!mkPs~Q?z#&);#j6B@l5~kaXU21l;CQe%r*@R+&F=ionunqacMixYO08ZQ#h^q1X;{+I7Y`R6K8_N5=AXtR_?i!(#zP&h6$u{#pJ8QzRaOurucY(<!=y2lD}k8C5fC$hiKo2=S&<wH6Tw-~nz-Xj%svt_mwk<lIR;)tRwxx*GpjsF-~kh$1Q<J&KCUKP^7{cbx!vJflU_!KfQWNh7*kP60rqK`fH!3vCTJA*OgYAtHqLlBAT%-|#41&S?e3T)lZx+X(!dWxc^brrM`tTIk_`s#O2mSW6AOr@IDGp@)g;&x;)D;V$?Xm|Hi<w0re-h?wO5#dk%8Z_SaVG9%J|!+D77pGX3DGJ3IQyv3JwPb=ft)qjbv;WA)&=sG)&wiporjz5QX%ia_K?EgVP3Fl<AMF$k`OZ+^Y|$$n6f-icAbaI@ARvz-|n@FIb&PfG+`mL-Rbr{xqUvM8Mex?`sZ3@3hPkyk}=}!}XdSO(q^HA{qlm>2l;*fZo(tVlAMZpgYARrbH?qSCjbv#VC~zsLGulHy%g9VJC1CD?BAH4BQOZo%Q%vC}9MEPI$%)FUETttu9t#(q|=81vB5)C1|GgJG#WB#(_a84<coY1|JZDKv(6gaGQ)^8BWZ799<%e{(EWs?Ad6soPP+rJly5RGGQqQ^x&esWx5&`5GH3^6`T$p+A0C&1I8yMo+n_YXB^0!C-6<d(=Gw`%<Z}z*nJTgCbUH;1L%#MF<C7KpUe&cql*E0wTHEN<s8CgkA5JZ^M1NK(Ba1I#0*$eQpu=6v{Q60c~}7#h*&&Xq&Ag%E~A$LHYKf99FEs{Sg6}&LdsaSJI4z=j)cCf7A_Jy<xBx^olL@)V3N!>s2t3P(&QTxUe{IQTRPn^^CHPE8F;tLnb<jEI~|A#A|RASVh*_q7Nabfp^DWh7qn4eha$t$ZoU5PPM0;LD1SF+*d@YFILS91=be<{O)Bap6?Kz}x=BUdq@r$8Q8%fmn^e?ID(WT`b(4y^Nk!eHqHa=AH>s$9p;VMrX4f(is=)9SNGHa?mjtR{lgLq5ht4^W(t{M(k2J?WZ7NEIQ1CDk(FMG0W)`|rHB|=^X$uIZ7eNM7gb)&16fz(dHv&(e5F+XwCL|>nYDbfp;-Kt^*kwt+0%0Y9S0gawF(@x(R9<VvKUgU9r>3GX{|uzWBxi($F(S?=38Xye%2-ScbWj_zRh4OpR$!slVuJJ8WZ3J~Q&BUbwqe|^L`-2kUN1!CjM1vY?pVJNQ8Y^lmt{T)<KcqR5X04iPEp%B`eV78mp+fPpk8qJIp!V41U(IB&DuE1Cr~nD(X6hUOqYY@bOmYi-R<PYp!|Ug+r@0nRlVc`G)=z`=6Jf%WHAUU=ypC@hUMr*X_oGthd+A#Ziyo441OLD>6sRt%uoP5;do!@?)pS47N1dO4bR=S7&fYSb}NTvh&X)|=6{S{9C61Pl%I}R(B?=*<BmLh*OAVkOW9@<jBli?VKgQ!A(lWt=yyClYn20AX?pJSH@!$F*SOV5yWo@7{B<`x{`+D&X(Z?&v3rnx`zVVN=IQw*t04PW2<<AZf}}>9rI#SoD#97-s7qx9UZXfE9Q;NBnE_xTJjzB(#u+#OoV3N9j4*P`eJwsU{k<r2TC7MT@fyD#)OUO1RmA)rE-?11)|lv7OKwiC=Huqj^W}23`0C`Ox$Jm4KRXF=al$P#$4puyp3!W1(|XTIV_CGivdorYl1l&Bo7>{Y`Le(7q_fC>(7Ml3=ItnNwT5+%`o`<I_PSk8ikVSHvu<hd=9a^_%4cQSb_M$$ov+S^VYw{lvn6$^4;%Lw$OI|+iMe&b_UX>nx6aDON=DQ9uvO@x9{8rs#gpQ~Nnr78TpA@ExU?JNIGrxxq{Hl}J8`5C;R3V$QS}D4u1Y=%BJm?BJR&w5f)MSb-+PE5neqHZb355AQYN$jn)EG(&@)E)jLwslb&F>gt%|pXu#HxC5b&x?wx_eSi>5vPb$ueD$2^2_4bSG&)ocjEAJxV*zFN*#r4g$FY=_+xZe?qd{q2t@WtsZr)_J<@k@6%>Cv|kz&3Nb)^V1_bQKE<}i!w5$Y@E)8l4A%|6juzS5>bu_v@{z*a*diLAWDRS+ZEB<H*0K-RvEt-Wgu1mHe+)~sS~^`@QFLki3QnWbK)#U1@A??zQTKJ3vPrEQn1WIWD;&n3HnuT?znihz<}lM?*mVJ-0|cV0EAE=6+U^es~jR|tU{z}vL}DfRf(DiTui*s5zk2^N-G3f4X)mL-`xk_xwQqD_{d5nuA*W}K~?lB5I33>a2rI09Kkndu%ZeN9twE8Ndoau$R6I|^|pzu=Cp+R!m9f1VO}q(FI6W8T(!8Di=d%!2TWvMp<eC5B{D)RqY=!O1oeOgDYT)vm5c-zZSkyqmd>=^sAru2x-r}*K(+SiLt6XadyjwqKdb37JTCJmCH;*5n-+Z0oc#-#dUF8NqdD>;X6EAu-?m>Q7-_XL?eTIBg7stgqd7xtQA_UB*10Dy!>m6)g2_)t%U8|mC#$#-4ZLB}%ygW18Wz7V`b%W{;6E=Kkludgb}ZgD=GRlhv1atozBaaRc0escT4fKYMGC=%(8`KS^upd>A)QRGUz1W|snZ)Mx`Cn_D7t~7KN*UEEz9||2~f-AMHx?Lohsfu?DyKsHqYBltm6e3WI5TR{~J!Klvl>lG8uWqH@ZiUe;tj-KSHvmw@#{~v$p?z^;yO(cL&r5RJ6)Tqud+S_fs1M<KX7G^!aEqkli@$sIdvm=pZhcu9i=h)7jQ#?FGLhoTtd)?87PK<@4#d3=z8~1oHt@_jhP$cz%hBXe@KU^G=4_-UV?Qv1E#in;3la(c?ZM{^La)<sAW<mJ3?J(44yzOAlNLlYC37-<m8)8n1E_8qqhEWYE1Qyqb_SIEO`T&%AD8$<gxg<Q`47ruTRAaCQz=J?=9I&CwsGA#X0206i-roP5C|56sG3LZ(SZ<I?40(kp~it3?^Mf!lUCN3jZNWImtHd&FKW!r2;zR$)A76G?+Er!i>b%DaO_DT7%bs}0&vdr%17Cf#@}U(MQ%zUl4metV<W>(5%-WWhgo0AVXBAvIT_dSQcb$=X^(65I>rD%Z7U=d`t82TH>|s~9Wu*(o5rP03ep+q6xa!fX3G_QygGzNCoq&ftHq#sjVg0zTo+fU&Qd|85VSJ)8XcmwWdH93Xql=rkN4_k%Bg!gGEfmfeXXu8!F;zx`YHDQ#_0vD8KL74Ks2oxst0fzaZJ?g*dGyDR&IWQ&#uR`&GY&Gr#+7l_l5#_G0ab9;EwL2sfCrfGB(+I#g&le(p9Z5tO2kCNqDs{x~t$vWq?*TR|%&F2(s)Uou#)};`;oW*ppyqHH^gTQpW0t;CWbsxD87X{<pWDyO!)A~E;WqagHp*5e$g`z_hDak5A&NcFw3iytQDwb?AOA<${Nj5s5FxZlf%5&Gw6&UW29=XiXH}G?|ZS)DWXM)iEqD)+Do!%VAV0+*Au5JQhIEI+#1lQa`UocFok3E<N)0EaJ<1kyG*`^D9EUmqBAtCu5$&)LMM>E`k0Avlt%?hy=<tRJb^mTMZsCByMG<uP)C*%%5A07SAYDBrP=I8Fr5y8YM*+_T%Wf=8MK$j>h|LT;;#Hn{||9Ha$4xM;7eOO*T2ImA=ot4GutFqW{axct6#Mm!ieM9I98+cNdr~9qGK97{~SvMY`v;8)YTW<TXEXmpq-K%Ty^n7;s>~vYu^84v|dBf=^&2XJ!3`S{rNt?emgy89FLiGX`Z|JOT2<EeTbGvQEb+Fw}r4{JO&kw$R@|OqS9%}Q$H2n@jhp;Y?x(_w^`A2Y{Q^u^_KeMJ<r~EI6&vi`e^nwxeWb%|V_Fwxad$M(k;OfFdt(h7a*QxdwuHA4lY9RK{_pI{tBBR_^%Lo|!-IE9ZegBjjYpvksV3UWBzI*V){nMThUU>em*VO|Kn)&0O-`wCQc&lILqh%oyvN&y6)Zs!9>(?6B!-A7Vf(Pv0PizSQ_5!Lo&yQBi*=l(ThX>yB)kl=0YkWMOo?RwO!&LqhQ8vtyFgm_Omuqx}gG9%xCbDV|bp&~XfM*wu^q0-LGn*r$S=#S<*_+3tyaYlo+SfVFkvu9#FGtJgM{S9S?r6djXK1ha_3Iyg*eJB^`(*tSdMNGNpOgNFqa#{Sy&>-()$C4|=dG0MALyA{O`bdl_U<3U7#ui6!*b{_;)d?<e7f~m>tZj5euWc!b&e<gy?v#$+jP6xp)OCx`3Tpp{x}Ns*3YQp#q^k8waLL-uWx)wlm5}SbZ|j3vf7q%gKfX*@NV~SzGPqFhzAdiL1V=GC&(x7AM0L7A9{wX)WLbrS|}$k%H+k4Ae$q9f;4@Av@Orpu|GkgwVn0iTw-q@4>Lv+xT1~yZ2kUeF>BiR#4SO#4t!ck79eqDTav8<mjKj(Ieqc)foq#-d{U>A&Kn&(_{QtncNcFtb7>F%m`=)QQm1b`zIQccsJ0~D{q;cGaV9KAfd0H(eh}^zQ)<4!h6Uoz?w7}3KmGoYQ`&0s{i7f6?|Zzh(?5Luuw~Tuj(>jo-H|)c;@+@#>6f;7{I{pyKYIA>qlZs_`RT#a```TS>HT|;zHRTz4>bSb>%XDlU%r1jeDc=^kB8s<^yrr-_kS9G`{<X4KRo*S+sm$d^5lo%z572s9TFGbN(wH<Ckf1LagxFj{V=MdL>ax~G+$Gc=WE<wQ-E#U-EuVT6%X3KzG?qzJ<aHRHk~gAxNi39Zu93c<zFbp`Q;beICb&Et1s?Q%Sk|V_r-8Xxu@aqi`$)W+r{DTymN85qoYdz;$)qQp_C^TK5MhF!}7;$x+q;Lpv?dbaKCw&kGjxcbbj6nH0W+T*!Grv8n6Mx{$@QC(7nbKvh<5Fn#9g_YDIUeyt<SR4!Q0~o}LezMTC?m5lXoJM4wY!pXEY3;hQWCohJ&hXjf`<M<#6`zP`Xo=M3xno0tDt(Q-b@KB@Jw?i<eaJ(zOZn(j0(uoO__>GF~W%kszOlrZ#~v`OtXciMh_67ePFrM6RGuN$?!D3nb?>p=OXMgN|*&#3+SKJUwL_GilLKJ1Tcdc{d=Tdwh5<pXAf?!)>iqy1#F#)|E|(&_`5cX?A|yw`sFMc2Kp7okQu2`X~vMGgl!v5Gsf{eJLq3BO-<;l-Ccdx@v!OdoXb=81Mr{ZtmKaVuX}ChxLWM%pi~@G@@ufjPhUcBxN#tl!f0YHr^p9Tx!OvXy=|ovp^WQ6BJT&n9&~{YRM$7=CQq&sN9hYxU7TgZ8iO2K17pX|W<B93p^C11+SL0<Bif;ww5NnNiH)P-}hdLBY{X;@|{E(;lL}({x^jwDd0@*D1~15wLM{dNLm(pdU^1Vqn`}mw?mda*W5I^XuPsE{Ur-fT8)V`EhfyU7p&E`EfdAOuJ3aFB;TtgV_b6+C9I3VXb>v3owoC>z3ig)G|AElvzfQzu4SewB5eG^Fgu0IcK%}kHikHxaE?J^j*Q@(3Srh=wUub^l+Xtt#{Ca7Ooh+haQp(>)!`Gxcr##!IcmQkGZ%ueq7eWI|B$mR^ELg1mS{#A-Vrd2=R&;Ca%Fh4qf@L0U`c#gb)~^5Z3Krh{YTbb`L`o!V%5h2SfZv#gMgGTpL3!>EWF*L>yySKNW^pt{C_Kkr+bN&?O%I-7$o&R1(4KzZ!;U^;u$w<=Pp$gCV$5JL&g8#Nu!>5v~g&!hB2+*;v$dL1bfD?+qf>icbV0w3>`Qx&Ds?5#yDyyNgz@2qMl%Wrg{d0}=CC#xgKM&%_>x2+NIPdm!S4mCn8gh%^b8j|U>!8%DhT`XI8ltoH;Fd8`EgR3M_I^#7p=5#g-1+?#8Fh&NJFxqyE)5V88R1d-MVcR@r;A-UND5%kB6d@mIFsPW9kq^^x3Ytwp96j8@aeKIOyoHt7UXQGH#LMf@mHBiJ03`nQ68x(n86fsmfmF=R4X`K266cJu?{vIfz^hZUJwMktcMS9bEZxk`sUy35XHE(~XXBS@h(hhU|%Vyc6Rkps5FclETO^ivqT(}G|8W)UkN@$x?w!yP(G~-HC%N5n{GP1bBy%bT=M}W;YLKiDf^y>+>Z|@D9OY`N!s?o0DcQ#)T|GF)w7Sc4eS-Q`e)}QszUS>3z7Mo%wTTjDvr7vBXH^o~eOqL=f>q>UE8ev2Xfg7%QvR+4NC65Ixkr_BWgq`$;q5<Qz811XDUWhzBKYqSEAMfAQ7vpnaLMNSEGB9%&nrUL0!vjMA&n@FY+Q@8S$$3|8DS=64OkraGuDV%bu)b}-wD-^h#~Qp=0YihQ;0^;~ZH(M$pN$u~D4vqHH4EiA$1o<rv`X-cH7Cwl*}Jt7oNwQHvtHqN)&bDg&6BK}s*Yu)7?Xu%pCWoK&Pk_?j~e&TwT5h|;H*k2d0taap>h{PtozTcwr@=<A&!@SEH4akQKdvzB1SqZNi~mbmfpr{wJh06iMuHlRdNLnt#VShx2M`OE^?*zZ)&t*2Q6*A;_aZ~Ez2wgA%zJ^s?1EVK`84~_EKh5LK2Qg7h}=XBGO)ZH40VXEoqO%Ju$SrM22pC%Ly)G{GcQzDMeq#JH?ra!37@;t5j>u85?9(R1vp2qn#>TQ%P4*D6dpJ+_nsC-vsOxBoPNCDbn(gi-?(C>mvS2RT`O$=aF&zuSGSiMC(#Okdt*07(=an$uUA`xj!^lkwhMpL>By*W66>#Z%1vl(wOin3aU$#d5SjL0EJm6q?XPr#RX=PgV|Kc_D4rvWpva*NtCeJvcg%erk2RyiAx0*6%F84ku$KFScNGzq!6hlI|j(hnw0YvV7qT8><W_TgOY@(EEVtr^l3}g*;H|=aw;I}OrlK$9K0M*)7N4!a3*`&Mbo*=Di50POQNnIi8&|<3pt0%4C$V0t$>JHlgELb`e2mIRA7+H1gArliQzVC;8ev_s94HAZZzM>y-gB(P!f0s<E^YVN0VZ-R30I70p<9jl?T7I!B$;@!c0~g!9*7LMMq&B%SG==qRbT}afdyZELx|S3C0CMXT?0RWWYgzb*li>mJB1MgT>5t72{%rO&a8*DzQIzR2yy_0=0(wom>hh3DgY)n~K<5%_SfdvPcb|BA84*W$kzXr3tQh4KACMr)t=&SlE#Y`zrCuzEzOJXoA5`QG%aT2PBEsQi(<?BT5@wsA>|E+?iOpsuGin>UvuSd*P`Hc%2JCucdygB!|&N8{^<rZKm3!m<}m2$1zbjj2G}_6$Yj{+Cjk=X;Q5T-jzvK7<`iEc7JT#+sEcGnB<xmu*zj25*6a4tpz0JX#(DB&kMIMz~2`E;Gnwu#<N7FK8k?h$sn#_B!{siW&js1ueyTtC{PM#F{5$g#6=CtLQMd7DlP)6#?(?OiI^~L1l+QY7mS3zRS<It(8ETker^U~<YWyIa|F?^4uBW0tD^maeX71%+7*WD;BuBwPq0E}c7cLO_f|;`Ly1lpb`2K~-<Kjl45)@VYb2Mp!q>#qP>_-|goUMoXe-R<1X}7NOY#~<au`WiElgQ&f>H+D)>co-2Q38w#UC1Wo1{x1!2xz$VK4#l3n1AWE}hKRFcN>*NO<s=4n9jbK~s}A$|(Fn)jBI+rGf)Wz)dYY=Hj!@!Uqoz6_|qt*##qc>(Fp^807^OQ#J_0sO*gc{jAUti}bBX0%Ow7Ccs+-zJ&_fzy$|i0Y!=d0g-1Hk>stI#t(yQbqv-REcc)vG03RkYHd~c2SJyXh9(HBm{5WofDzz~66{D|U@*Zi_!}qRD#&4Qg-=g{<IxMEJc&7CBbOdbopwvW-xv>qQw4|x+{27qZpbv|E;OUU1tWR8AcwKFM1T`u3Ore$dsQr1rvyI>*<qj(?My&q1dO3N4W5#T{A13*KPpo%j?LSx<S@7b&5Z?tPK*lfTQWq1!4Lr+pE(IsV+eUU2RAD`YXzPlFnS1k0w^5!*BG0_;3_!K!+8V=-Y}Uh1>KN9;U^2`!709Aun)!I{sX2~L_8}rn2~X@IDd_?ISj4^(-jWhB}<`OQ30Cw7>dL*{;)ZTO#5KK_mXRb4@jbBOf*Q!bCTjZV{;f>At6vA;J(Fyo(Rp2i8+;m;HG%V6w?we7vc#}e+5(leSr>hrr~DS85?)W1Wpb&s*pn&?pYLYvYsKnE(oo7G?>x0D7Y98C1@aAb_jqFBooc{<{D#j7+k9k2>BdC@C(?Kl^2~A?LGm;2e>(jFie79yHaUmd#?mlP}2Yutzk|39@yx&dSG!FTyw5Ax)404O+6%q5^y+(je~;|j?jipREQjWiSoyl8@M9Gov9#N1yR`7h<~e%h{M>5pbp^_5F40n8N97!mdglG^%_jc6q(5zN!*;fz#X6^f=5$!PDSYH-G@dT##U8CCZ1Xa{Ju^h!S69B!ob;r&f`Ra11NAgOjG7WaEd%q5FC@9hk9XX-s)|{VQj56XGi>kasvv0uLQ^$%poHT&Omx2Ba2KK`Tzw-FdCd0FF6CnhS#~q&>V)=z+*KEIGPJdQ!#n6;hfiylcA^r;{}2wSOl2_{s$7t1YnAZDF=Ivp}7QFMfC#nlv0~aNBCDn+!CXpC}9CN69R+#qvc=$Y!RB0k|S(KxW`S97h+)k_E}>tOABal4NZHV&~7G(>@w6ssY@O`qU{18(?QCZtq2^%mDUqx9kox9SGS*_;BSp>guNu(gFbu-An=;<xe~Jh;1Ln{Q8EXfEg%@p1z=mfhE}rmWLHoNqU2C6WK1t(i`}<WC-WxqjMMz;0!=f4uv-8|G@x9iHi=6SE<%_LK7cr^Kykphf+(3x)C6Bm4kCK7&q*x5f+XUgB!L4mq6AjJ;lSl4Dzi@8sDL{MK)NUz<i0TBK=i9{@C3miCRNoV{8QpuN|B#JDS};=qG;bcw1uTkrZh+=m*u-H2r`1Z2rfus$jZnO0YP9fE~=<BLSwIdb|JzK1ZPP`5IovG5<0tT?(=|1mt}<+v1Lun13V-e17^Z#H$zIeKs;_d22x_;Qz20n0n6UnD160y=OOI}J)Egar}hD<UX031`l|C#lDtT-p##J~h$=wOiUfsGwm2~R;6;(3zoK$bS<r4or*L0Md1WnFFzjxhF?fAdvBah02NtbC77fB+UM#(<fC#xH#H|rtA}eX4gYVRt7kDKtJP5bRO%69H%P!c|)kV5&{B%ZO#xZId>e9v}_%shXUWH&VbP$VZy)d-FM3bpS_+&gnc|jZFnX(T<2(!%9g?iKQ8A|c1XmT}VP+SyDGfUX$Sn&$6ng`)wA(-eLf=bYGqcA%Rn6p5XfBpF<Kfn1WKg;<iKjr*;hXGWd-vFvlHGq<<cM$4L;};S5XWW)~1eqcbGB{Zfb|avHOtkL_SPPXwWLi64rG#Tvnrn<^3g$h=Pk(;nr$5K>)1Pwuj6d*d9C9=}hWw+@>VO#pE605yiybE;yp@c(&}?-{U+wTh8|GxepcD$h$j?ANoG}(ykRdiGpN&EBvd{jlJt)d@zM4?wi2O!bl(97g+DOWpf>;EMO$*0q{}vDaW+9F9@O8j0us=ilqS2duNt=B|9!<aCV>X|jPn+Th{Vq6E{<DVhf@)L#&nk@DLKba-)c$x^Vdp|U?~hf8=aQXd`c-G`&dvR%Ds7#Zbv@0^+7+;GYug1ZU7OK_s$XvQ@ldVb?@zBL=d{vfyIN<rPs^c_o9x&c38Qp-JG;<|E!xt#+uMaID?DE<^YrE9z)G7pR_VQDCErf5@C)ntex>b^7G?R{;pKc+U2FHQ3+>n?OYC;V*<E6{^C0^l9Xfg+p%g8bV&HhR4(BSx(+@4Vn@lfTao3%>`hvU53$?cukPj`n+f~8N$~)slw}f!L_O35g-q%pw!q2W`aaW(ETft<G*|B5R9d~7i`_scknB+M9V`Ixy>EwehLn0}s^Eg7hKN)V-dU-KgjGDqSU;RpzSw@TLcuW3ueO}TSCSvL8=~J2F>3ldFwOb6$r!)@3rmRa-J7qNQ=2XT{X*pb%pq;D-w8yK>HaTglermVUtZZ+%)2t?Imltjoguf_G0}M?qoy9DqvMbOCm@%)R-G1O#T2<GUr0MIytS@VAt}MU$wcQXvSm|4<m`w2)FPrVo)`r^++gjX97S8nx0Lj&NwV>M)Ku3RH9I1AgX5;Yc<$QGZy!&+X*sx>PZ|(I4htTbj)IZ2p2^;nXcX1K9yB)FimJM$ZysvWeL05~t374C~IUjVHSXX#_z4O&}C8ECGPz>pJD(VAf1YL&hQs{kg`1Cw1&t}VEzvb7a!3-u%-M2eC^_y<3k9WXT`pvz@A(nB6S$}Vu3^uDG2aT7!JLpQS-|H~rWW(F;4kpt9WE>CH(`(z<sQA&aqUH4EM#lBoR_*<C*wy@Xf7{xq?ZA&T-Fi|t1n>>lv}(O$Sg$x}ehJ65*)(e#ZJUbqTWar*cV(Ko&DM5m#V4&I&(&#FB)v=F+RB{4dK?Rson<Zx=d*T}u(r~?H=q!q67~1(%IgcaX$v@Yb-J%ymHR?B<kp5Cbp7XnyKI+(*Os=7c75%yw(1=O0RW{!I}Y@<<hPZ)-E`YQCC4IWp-~~2VylPZas{Vk(bNi-tFwzN<!mwiQx4$4o&or2ljTrjYamVE^Fkje&<b$)tMlg8Jywk-3z|S1@6_+yz8${_<v4di02O2axn({AY(xbpS>w6S2#X4|7NrVOz-OB5oYI6%8PQDZmjmsEut>d!X}uVz3{ivCYyjcTM@`+^K|A-G8JNalbUp}ix>^oa1nc8hpss^<&*Z^*0bEQ*i}T&dx!L^f*)1XE$xlB&eEQ(W`@?S^{B-}`(?>u3ZP0F-F?ie*pBrrLiEyF3zrbi}b4d+<7Nl2{_i(w`g6NChx0@8A1}qwSb0{zxvD+O8s$SBb4sh<kL2%YZw|U35t`%5@EWv4dQ(jYvF$-sTqAk}8uZW~g35W}s<W-d_SVY875F3HaSYO*gzvv}f2Q=KSdbhpOTnO&9_hRRb)jQV2+j(z<$xflZsUoD>tl+i43B=eXN)|$j90r@b6d@vdD~7-$Bec~{a#ve@^<Fn5aE--i&&jr%)`I?Y8!mP`qz-3W`xtift5bJx7Y8V1x4_;vFF^|V^$kpJc3A0Sq7OV;9sla3q$+^zz6>1<HjmP<pT5arHKY7NOAZ@B9?e4<m%;tV_kY0jX^0%5&7ilm0er&X9?XKOj=vfN7(cP{FnGLXMn_$*@Qz(?0Iekf#@bJIyNxuJ76&^N5L(ZL{4XfuMcCDjcH{+Z&Po{izSc6@fIBK{LQWM3;w5Gq2ih619`B12h88mFB8h-syv1S6y%L#gcc$12N}JMv`&(5|@VdLB)_O;uIW#aoy2duMZ{C4wH~c*qyY2;@TU%Z22?svC0P$Re&rGh(#w)Zp%j7(V>E|NhI&%0t2X-yqXE(HK$v&IGZCGtvTy~ADodbSb_}0O0=Nb?Lv<a}*vmtIh;`~VPr-FSY#aF`ocS}C{ZH6|VqtXuCz*KrLVAjzVRCOB=?U39nZ-;$(Ua+edd(`!O!rQTGIsI^5O_m<3`(@aFP1bx&)F143gxuK}C}{jgpXJd0=`v+dJds=gnpcohF1Zz;o-9YrW6q@_97SNNm8+GP+7^IVOzZMxXu^y&8QM}j6$Kt{Eq`N5>1L^Ob7CWE^9Hp!hU?FEx2|$3mL%xo6xO`N3ZV7y&oMDWSy|<Xk`=_Txr(GBEmTpy_#6~P11WSWLu5z6Y9GYXuF_kf)LsO2XRArC!vjrL%jr2xB+<F~wqqiW-ri|VVLM_7SGwFIh#w>>==$A~u0OKN`yD*9rDbu#lMV%^G`1C#e-9Di026|hhVOIct2Dy7NS{*0><sImVvpYRsvS<c*mkXk&E9QSP(x0IR%M%ryR%Gd`M|3r)WNu8MkP-{2@KZL)~Fa9BLzsA2C48c;jS{;)zlCbZ!(448to7s1}1&NTn^RKx_uGp!;cbmW<s*+b5zNACSp)9JmvatK6}fUjV8O~+Zdoqm&yRC>%z*dFvAs5IRaE^5d}w8EmTh5X=NQS0th<{!Vb;aId(Q$4&!(ly9#3#@vADDMb&)W$#f~jB}r?x=({eZ!AFg~@apHiUtqj`BT}uum+w<xE&30e*A0h4<ik7GZ_stvZu{L_-*ftA@2!r%{T)h0u&}FmySuKn>EfvAVjH)+OAoz8EX;XM3#@e#m~$c;u7Wkf2HL3CY0zA0tw#(QjV;xuq+Cv>C_uXKS?%vxxW+zj%@ri03lFXiVLJH=1}!|T^fk<;+)N8Z@P^UXjMdRMH%h^d0N)5)D$S25YP7NW(De0oJWYl>-hKZgyKjBl{d-1z+3a^O%Ya#V{w|x0?!Iz6SV7@l|Hg*x9NyVa)cH5R2%-~DI%9fv>z@M}iqlWFN6A)Y`~iZm`PqwKfBSRpe)M2)^v&QX4Z1q~7?QjA|Csb~3?Gic|B~JL;uG$d^2P1D6=B|>z1wkjn_*`Ny_{6-|L#1D7G==x-**3x(X!cp^2^(|2S-P3wr#MzE%u(=U5CvoPz=K8Y(gHW*|KwSI+@~73s!{br@uZ4%fW^l4u~7dub3J9<;SPLHBG0puI1z;(2?0FpLUjr-x6(F_T^+X9^Y;|hBcnD6E=9gYmJY)tX6N3d)xJF8O#2e{ehe=?$B-S&Q7O`W1{NqZVF%A!LN^oKYjb?;SYcNf6dS9tXcc(!$;pe`r(I1zudmNpi3+D^5yLI-LN2I7%YydN(3J6lr=er=G`A1qny<LVpA}NJ726OecHa?<6zKkZuQ08$>|pd$K#8;xLIgY{9jH;$nS=a{(2{m=EIs#XLs6E{IJ{EXmR=-af;i6=^PJweEvJy;VL$@TCcCUeK)V4eRAc;-nxA2`SZ1(e{Zjc!8$G4JaA3Vr!Oa8<~!^Ty_&q;9YbGqj2`C_F~02OxYPV_Mn9m%@sr_$A0K^t|I4*Vw{M@Ge%bckcZlxNc)BRm-TLR*?GHH#-qLb2Ib1(E3g$1=wV52<)VQ#d?;G}ie}nJXc%Aul+B(z+lNZxAHtZZn;nme_xX#8Z&SmtWW(L5D$#9piRGVjai{UYTEBWw_*PVyj+ws~sT7R$2o6GLd=8zbcZHKnm33GQzz<LMFz4ZXi=8|9M3_`s4E}W0Xqi!+5*WV3)e)!=3USZw9x4kKEqV#v$$(;74Y#*WDpYmrgp6@{aHl37a%gwyIhM*n8hJuc02a|p3!Z)mIO-(N|j@O5IChfd;MViUI(TCXFbaqvm86>Y<yF#y_Jk_(0!h_m5u=i9_^Vu1K6i45vdfJgWTl)OZM$l6P0Qpjy>6m@HV3)E?&0VCsh>SU4T+RqZC@P8caU{<<6kS9Ht(36l=xX#Tq$ruD51_2P63g^gVVPH1H1r0Z`7Y#<-O$Dx+W6sUV@C!L(?fPc3~z|xzXdUTUo-!NB=3WfIQH*O-*y*#UWdEo(c%-6x8>H_kn80Lmq%R>SLALcdSQhNJS!Hep?Vnz9y0ey_+q%1nnj+p4aKUYIV;9ht(5W7Yn4O2a*FVvV1H_cu>Gd&CPR2b^=_!%O@{D>2;LCEn+)MihVb7$L%3cpdNqQ%Qw^ZK_Nr+?N%aMk@UAAFxPr08N(E89sbHN-fK)2bH=}&?Ql+41jW3VZX%U^)mr_gS<(q}Nj8<B2tu7^7CQ6k`fH&qWb>$`S;I(umTET6Rl}T&i!LwFWUN_@!8I8Ewi)Ve461?GwHz~oJT*>F^$PQ}v-y(rhM{ECejTc|d)mL<Gs!A_xl{sl+s0tojmvV3~(nZC!@}7z~rXWo8-sLJo;<_juz_XlJ@~Y15f=qv^Z}aZPx83-*8{c;0+irZ@r}k}4sgk#Rse9R{dd&xV&nCC-G&jHX)vaIYfqr{7`L-<5d^Dp*r$0904C0hNWX*$CtO0$l80P7DpXYft`I?qtoOWM79>W68%JSLd+2q$Jt>ozT>8n{eU0@cE%d-h7=d@AGq_OPo=SIt?jfN-tLwS057%#LV<3D8<vEqeOkGt<IPifb#$=VbA$p8%R_-_Qk&u+al2xBNFFGlm}giQGK@!y_)|LEbjj~+h#<);Tv?|<{Rr}ytY`u6@Q-);8&qaW{|p1cV26EgT$80;2#PN$Rpt<w4!7{;l91;Q4ltK}0wIURw4^k8|q3zU;J^qqoA{n-EB!QCl)Ht8u0&i@xW?f~NyU@^G_!A^VhnrtB-+ztKS<74yduMgVKj4)+>2~^qW8<;+@ZgfQZtgYwPt=In_JSTyI'


def retained():
    return json.loads(zlib.decompress(base64.b85decode(FIXTURE)).decode())


def request():
    return {'schema': 'merlin-browser-runtime-request/1', 'operation': C.OPERATION,
            'request_id': '2fbf6605-4eb8-4820-af10-f021288dcb17', 'created_at': '2026-11-21T21:30:00Z'}


def execution():
    return {'repository': 'morganaspim/Cace-app', 'ref': 'refs/heads/merlin/browser-operations-20261121',
            'runner': 'cace-oci-a1', 'run_id': C.OLD_RUN + 1, 'run_attempt': 1, 'workflow_commit': 'd' * 40}


def publication(episode):
    return {'episode_id': episode, 'status': 'completed', 'sources': [{'observation_id': 'o0001'}],
            'qualification': False, 'promotion_authority': False, 'model_calls': 0}


def readback(episode, content=None):
    # Simulated response. Actual captured arXiv text is bound by a SHA in production.
    content = content or ('Attention Is All You Need NASA News OpenMDAO ' * 5)
    return {'episode_id': episode, 'kind': 'text', 'encoding': 'utf-8', 'content': content,
            'artifact_ref': {'sha256': C.B.digest(content.encode())}, 'capture_event_ref': {'sha256': 'e' * 64},
            'title': 'Simulated source fixture', 'total_bytes': len(content.encode()),
            'document_status': 200, 'qualification': False, 'model_calls': 0}


def launch(episode):
    rows = {}
    for role, network, memory, cpu in (('broker', 'no', '134217728', '25000 100000'),
                                       ('renderer', 'yes', '1073741824', '100000 100000')):
        rows[role] = [{'User': '980', 'PrivateNetwork': network, 'NoNewPrivileges': 'yes',
                       'MemoryMax': memory, 'MemorySwapMax': '0', 'KillMode': 'control-group',
                       'cpu.max': cpu, 'memory.max': memory, 'memory.swap.max': '0', 'pids.max': '128'}]
    return {'episode_id': episode, 'status': 'succeeded', 'all_workers_stopped': True,
            'scratch_unmounted': True, 'live_unit_samples': rows}


class RequestAndRetainedTests(unittest.TestCase):
    def test_exact_fixed_request(self):
        C.validate_request(request(), execution())

    def test_request_cannot_select_urls_commands_paths_or_budgets(self):
        for name, value in (('url', 'https://example.org'), ('command', 'echo'), ('path', '/tmp/x'), ('budget', 99)):
            with self.subTest(name=name), self.assertRaises(C.B.BootstrapError):
                C.validate_request({**request(), name: value}, execution())

    def test_prior_request_identity_and_wrong_operation_are_rejected(self):
        for key, value in (('request_id', C.OLD_REQUEST), ('request_id', C.A.OLD_REQUEST),
                           ('request_id', C.F.OLD_REQUEST), ('operation', C.A.OPERATION),
                           ('request_id', 'NOT-A-UUID'), ('schema', 'new-schema')):
            with self.subTest(key=key, value=value), self.assertRaises(C.B.BootstrapError):
                C.validate_request({**request(), key: value}, execution())

    def test_bad_timestamp_rejected(self):
        for value in ('2026-13-21T21:30:00Z', '2026-11-21', None, True, '2026-11-21T21:30:00+00:00'):
            with self.subTest(value=value), self.assertRaises(C.B.BootstrapError):
                C.validate_request({**request(), 'created_at': value}, execution())

    def test_fixed_runner_branch_repository_first_attempt_required(self):
        for key, value in (('runner', 'other'), ('ref', 'refs/heads/main'), ('repository', 'other/repo'),
                           ('run_attempt', 2), ('run_attempt', True), ('run_id', C.OLD_RUN),
                           ('run_id', True), ('workflow_commit', 'main')):
            with self.subTest(key=key, value=value), self.assertRaises(C.B.BootstrapError):
                C.validate_request(request(), {**execution(), key: value})

    def test_exact_retained_failure_is_admitted(self):
        fixture = retained()
        prior = C.prior_receipt(fixture['receipt'].encode(), fixture['partial'].encode())
        self.assertEqual(prior['execution']['run_id'], 44946846703)

    def test_retained_hash_mismatch_rejected(self):
        fixture = retained()
        for receipt, partial in ((fixture['receipt'] + ' ', fixture['partial']),
                                 (fixture['receipt'], fixture['partial'] + ' ')):
            with self.assertRaises(C.B.BootstrapError):
                C.prior_receipt(receipt.encode(), partial.encode())

    def test_retained_semantics_fail_closed_even_under_fixture_hash(self):
        fixture = retained()
        original = json.loads(fixture['receipt'])
        changes = [('status', 'installed_native_passed'), ('after_failure', {}),
                   ('native_acceptance', {'status': 'passed'}), ('model_calls', 1),
                   ('system_package_mutations', 1), ('python_package_installs', 1),
                   ('public_worker_shutdown', {'all_stopped': False}), ('fixture_reused', False),
                   ('rollback', {}), ('package_failure_observation', {})]
        for key, value in changes:
            candidate = {**original, key: value}
            raw = C.B.canonical(candidate)
            with self.subTest(key=key), patch.object(C, 'OLD_RESULT', C.B.digest(raw)), self.assertRaises(C.B.BootstrapError):
                C.prior_receipt(raw, fixture['partial'].encode())

    def test_only_one_prior_arxiv_attempt_is_admitted(self):
        fixture = retained()
        value = json.loads(fixture['partial'])
        value['public_cases'].append(copy.deepcopy(value['public_cases'][0]))
        raw = C.B.canonical(value)
        with patch.object(C, 'OLD_PARTIAL', C.B.digest(raw)), self.assertRaises(C.B.BootstrapError):
            C.prior_receipt(fixture['receipt'].encode(), raw)

    def test_budget_derived_from_three_exact_prior_episode_directories(self):
        value = C.validate_episode_budget(list(C.EXPECTED_PRIOR_EPISODES))
        self.assertEqual(value['remaining_public_attempts'], 2)
        self.assertEqual(value['prior_fixture_attempts'] + value['prior_public_attempts']
                         + value['remaining_public_attempts'], value['maximum_attempts'])

    def test_extra_missing_duplicate_or_unknown_episode_blocks_budget(self):
        base = sorted(C.EXPECTED_PRIOR_EPISODES)
        for value in (base[:-1], base + [base[0]], base + ['news-nasa-extra'], base + ['unknown-fixture']):
            with self.subTest(value=value), self.assertRaises(C.B.BootstrapError):
                C.validate_episode_budget(value)

    def test_new_host_and_unit_only_rebind_existing_runtime_and_directory_repair(self):
        fixture = retained()
        host, unit = C.new_active_state(fixture['host'].encode(), fixture['unit'].encode())
        expected = json.loads(fixture['host'])
        expected.update(release=str(C.B.PREFIX / 'releases' / C.NEW_RUNTIME), runtime_manifest_sha256=C.NEW_MANIFEST)
        self.assertEqual(C.B.decode(host), expected)
        repaired = C.A.repaired_unit(fixture['unit'].encode())
        self.assertEqual(unit.replace(C.NEW_RUNTIME.encode(), C.A.RUNTIME.encode()), repaired)
        self.assertIn(b'ExecStartPre=/usr/bin/python3 -I -B', unit)
        self.assertNotIn(b'RuntimeDirectory=', unit)

    def test_runtime_delta_exact_two_members_and_origins(self):
        fixture = retained()
        delta = C.validate_runtime_delta(fixture['old_manifest'], fixture['new_manifest'])
        self.assertEqual(delta['unchanged_payload_count'], 12)

    def test_runtime_delta_rejects_importer_policy_or_extra_changes(self):
        fixture = retained()
        for path in ('python/merlin/browser_ingest.py', 'python/merlin/browser_policy.py', 'bin/launch-episode'):
            changed = copy.deepcopy(fixture['new_manifest'])
            next(row for row in changed['files'] if row['path'] == path)['sha256'] = '0' * 64
            with self.subTest(path=path), self.assertRaises(C.B.BootstrapError):
                C.validate_runtime_delta(fixture['old_manifest'], changed)

    def test_runtime_delta_rejects_wrong_product_origin(self):
        fixture = retained()
        changed = copy.deepcopy(fixture['new_manifest'])
        next(row for row in changed['files'] if row['path'] in C.CHANGED_PAYLOADS)['origin']['commit'] = '0' * 40
        with self.assertRaises(C.B.BootstrapError):
            C.validate_runtime_delta(fixture['old_manifest'], changed)

    def test_recovery_serializer_matches_frozen_canonical_format(self):
        self.assertEqual(C.R.canonical({'x': '\u03bb'}), b'{"x":"\\u03bb"}')
        self.assertFalse(C.R.canonical({'x': 1}).endswith(b'\n'))

    def test_launch_requires_native_isolation_resources_and_stopped_workers(self):
        value = launch('fixture')
        C.verify_launch(value, 'fixture')
        for key, wrong in (('all_workers_stopped', False), ('scratch_unmounted', False), ('episode_id', 'other')):
            with self.subTest(key=key), self.assertRaises(C.B.BootstrapError):
                C.verify_launch({**value, key: wrong}, 'fixture')
        for key, wrong in (('User', '0'), ('PrivateNetwork', 'no'), ('NoNewPrivileges', 'no'),
                           ('MemoryMax', 'unlimited'), ('cpu.max', 'max 100000'), ('pids.max', 'max')):
            changed = copy.deepcopy(value)
            changed['live_unit_samples']['renderer'][0][key] = wrong
            with self.subTest(key=key), self.assertRaises(C.B.BootstrapError):
                C.verify_launch(changed, 'fixture')

    def test_source_content_status_nonclaim_and_exact_recovered_bytes_are_enforced(self):
        value = readback('fixture')
        C.verify_read(value, ('NASA',), exact_text_sha=value['artifact_ref']['sha256'])
        for key, wrong in (('document_status', 403), ('document_status', True), ('content', 'NASA'),
                           ('qualification', True), ('model_calls', 1), ('encoding', 'base64')):
            with self.subTest(key=key), self.assertRaises(C.B.BootstrapError):
                C.verify_read({**value, key: wrong}, ('NASA',))
        with self.assertRaises(C.B.BootstrapError):
            C.verify_read(value, ('NASA',), exact_text_sha='0' * 64)

    def test_non_native_execution_rejected_before_output_access(self):
        with patch.object(C.os, 'geteuid', return_value=1000), patch.object(C.B, 'operation_directory') as output:
            with self.assertRaises(C.B.BootstrapError):
                C.run('/not-read', C.NEW_PIN, request(), execution(), '/not-created')
            output.assert_not_called()


class SimulatedNativeSequenceTests(unittest.TestCase):
    def run_sequence(self, mutation=None):
        request_id = request()['request_id']
        result = {'status': 'started', 'public_cases': []}
        budget = C.validate_episode_budget(sorted(C.EXPECTED_PRIOR_EPISODES))
        recovered = {'publication': publication(C.R.DERIVED_EPISODE)}
        calls = []
        response_text = readback(C.R.DERIVED_EPISODE)['content']
        state = {'after_restart': False}

        def invoke(release, value, logs, name, uid=982):
            calls.append((value['operation'], value['episode_id'], uid, name))
            if mutation:
                answer = mutation(value, name, uid, state)
                if answer is not None:
                    return answer
            if uid == 1000:
                return {'status': 'denied'}
            if value['operation'] == 'status':
                return ({'status': 'completed', 'publication': recovered['publication']}
                        if value['episode_id'] == C.R.DERIVED_EPISODE else {'status': 'not_found'})
            if value['operation'] == 'submit':
                return {'status': 'completed', 'publication': publication(value['episode_id'])}
            return readback(value['episode_id'])

        def command(argv, *args, **kwargs):
            self.assertEqual(argv[:2], ['/usr/bin/systemctl', 'restart'])
            state['after_restart'] = True
            return b''

        def regular(path, maximum):
            return C.B.canonical(launch(Path(path).parent.name))

        with tempfile.TemporaryDirectory() as temporary:
            logs = Path(temporary)
            with patch.object(C, 'wait_socket'), patch.object(C, 'invoke_native', side_effect=invoke), \
                 patch.object(C.B, 'command', side_effect=command), patch.object(C.B, 'regular', side_effect=regular), \
                 patch.object(C, 'ARXIV_TEXT', C.B.digest(response_text.encode())):
                error = None
                try:
                    C.native_acceptance(Path('/simulated-release'), request_id, logs, recovered, result, budget)
                except BaseException as caught:
                    error = caught
                intents = sorted(path.name for path in logs.iterdir())
        return result, budget, calls, intents, error

    def test_recovered_read_precedes_only_nasa_github_and_three_restart_reads(self):
        result, budget, calls, intents, error = self.run_sequence()
        self.assertIsNone(error)
        submitted = [row for row in calls if row[0] == 'submit']
        self.assertEqual([row[1].split('-' + request()['request_id'])[0] for row in submitted],
                         ['news-nasa', 'repository-openmdao'])
        recovered_index = next(i for i, row in enumerate(calls) if row[3] == 'recovered-arxiv-read.txt')
        self.assertLess(recovered_index, next(i for i, row in enumerate(calls) if row[0] == 'submit'))
        self.assertEqual(len(result['post_restart_reads']), 3)
        self.assertEqual(len(budget['attempts_started']), 2)
        self.assertEqual(len(intents), 2)
        self.assertEqual(result['status'], 'passed')

    def test_first_source_failure_stops_before_second_without_retry(self):
        result, budget, calls, _, error = self.run_sequence(
            lambda value, name, uid, state: {'status': 'failed'} if value['operation'] == 'submit' else None)
        self.assertIsInstance(error, C.B.BootstrapError)
        self.assertEqual(len(budget['attempts_started']), 1)
        self.assertEqual(len([row for row in calls if row[0] == 'submit']), 1)
        self.assertFalse(result['public_cases'][0]['acceptance'])

    def test_lost_submit_response_is_consumed_and_never_retried(self):
        def lost(value, name, uid, state):
            if value['operation'] == 'submit':
                raise TimeoutError('simulated lost response after submit')
        result, budget, calls, intents, error = self.run_sequence(lost)
        self.assertIsInstance(error, TimeoutError)
        self.assertEqual(len(budget['attempts_started']), 1)
        self.assertEqual(len([row for row in calls if row[0] == 'submit']), 1)
        self.assertEqual(intents, ['news-nasa-attempt-intent.json'])
        self.assertTrue(result['public_cases'][0]['submit_started'])

    def test_recovered_read_failure_spends_zero_new_attempts(self):
        _, budget, calls, _, error = self.run_sequence(
            lambda value, name, uid, state: readback(value['episode_id'], 'changed')
            if name == 'recovered-arxiv-read.txt' else None)
        self.assertIsInstance(error, C.B.BootstrapError)
        self.assertEqual(budget['attempts_started'], [])
        self.assertFalse(any(row[0] == 'submit' for row in calls))

    def test_unauthorized_peer_acceptance_blocks_before_acquisition(self):
        _, budget, calls, _, error = self.run_sequence(
            lambda value, name, uid, state: {'status': 'not_found'} if uid == 1000 else None)
        self.assertIsInstance(error, C.B.BootstrapError)
        self.assertEqual(budget['attempts_started'], [])
        self.assertFalse(any(row[0] == 'submit' for row in calls))

    def test_second_failure_consumes_two_and_never_replays_first(self):
        _, budget, calls, _, error = self.run_sequence(
            lambda value, name, uid, state: {'status': 'failed'}
            if value['operation'] == 'submit' and value['episode_id'].startswith('repository-openmdao-') else None)
        self.assertIsInstance(error, C.B.BootstrapError)
        self.assertEqual(len(budget['attempts_started']), 2)
        self.assertEqual(len([row for row in calls if row[0] == 'submit']), 2)

    def test_changed_restart_read_blocks_without_new_acquisition(self):
        _, budget, calls, _, error = self.run_sequence(
            lambda value, name, uid, state: readback(value['episode_id'], 'changed')
            if name.startswith('post-restart-read-') else None)
        self.assertIsInstance(error, C.B.BootstrapError)
        self.assertEqual(len(budget['attempts_started']), 2)
        self.assertEqual(len([row for row in calls if row[0] == 'submit']), 2)

    def test_no_third_budget_or_previously_started_attempt_can_run(self):
        for budget in ({'remaining_public_attempts': 3, 'attempts_started': []},
                        {'remaining_public_attempts': 2, 'attempts_started': [{}]}):
            with patch.object(C, 'wait_socket') as socket, self.assertRaises(C.B.BootstrapError):
                C.native_acceptance(Path('/not-used'), request()['request_id'], Path('/not-used'), {}, {}, budget)
            socket.assert_not_called()


class SimulatedRollbackTests(unittest.TestCase):
    def rollback(self, *, active=False, stopped=True, pointer='owned', stop_error=False, attempted=True):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            release = root / 'releases' / C.NEW_RUNTIME
            current = root / 'current'
            if pointer != 'absent':
                current.symlink_to(str(release) if pointer == 'owned' else '/unknown-release')
            properties = {'MainPID': '123' if active else '0', 'ControlGroup': '/group' if active else '',
                          'ActiveState': 'active' if active else 'inactive', 'UnitFileState': 'enabled' if active else 'disabled'}
            receipt = {}
            attempts = dict(host=attempted, unit=attempted, pointer=attempted, service=attempted)
            with patch.object(C.B, 'PREFIX', root), \
                 patch.object(C.A, 'observe_supervisor', return_value={'properties': properties}), \
                 patch.object(C, 'observe_workers', return_value={'all_stopped': stopped, 'units': {}}), \
                 patch.object(C.A, 'restore_after_attempt', return_value={'restored': True}) as restore, \
                 patch.object(C.B, 'command', side_effect=RuntimeError('simulated stop failure') if stop_error else None) as command:
                safe = C.rollback_active_state(receipt, release, b'old-host', b'old-unit', b'new-host', b'new-unit',
                                               root, request()['request_id'], 0, attempts)
                return safe, receipt, current.is_symlink(), restore.call_count, command.call_args_list

    def test_confirmed_shutdown_precedes_owned_pointer_and_exact_state_restoration(self):
        safe, receipt, pointer, restored, commands = self.rollback()
        self.assertTrue(safe)
        self.assertFalse(pointer)
        self.assertEqual(restored, 2)
        self.assertIn('current_removed', receipt['rollback'])
        self.assertEqual(commands[0].args[0][1:3], ['disable', '--now'])

    def test_live_workers_preserve_pointer_and_configuration(self):
        safe, _, pointer, restored, _ = self.rollback(stopped=False)
        self.assertFalse(safe)
        self.assertTrue(pointer)
        self.assertEqual(restored, 0)

    def test_failed_stop_preserves_pointer_and_configuration(self):
        safe, receipt, pointer, restored, _ = self.rollback(stop_error=True)
        self.assertFalse(safe)
        self.assertTrue(pointer)
        self.assertEqual(restored, 0)
        self.assertIn('stop_error', receipt['rollback'])

    def test_unrecognized_pointer_is_preserved_for_reconciliation(self):
        safe, _, pointer, restored, _ = self.rollback(pointer='other')
        self.assertFalse(safe)
        self.assertTrue(pointer)
        self.assertEqual(restored, 0)

    def test_failed_preflight_does_not_stop_unexpected_pre_existing_service(self):
        safe, receipt, _, restored, commands = self.rollback(active=True, pointer='absent', attempted=False)
        self.assertFalse(safe)
        self.assertEqual(restored, 0)
        self.assertEqual(commands, [])
        self.assertIn('pre_existing_state_error', receipt['rollback'])

    def test_worker_observations_use_distinct_paths_for_success_then_rollback(self):
        paths = []
        def command(argv, path, **kwargs):
            self.assertNotIn(path, paths)
            paths.append(path)
            return b'MainPID=0\nActiveState=inactive\nControlGroup=\n'
        with patch.object(C.B, 'command', side_effect=command):
            for label in ('accepted-workers', 'rollback-workers'):
                self.assertTrue(C.observe_workers(request()['request_id'], Path('/simulated-logs'), label)['all_stopped'])
        self.assertEqual(len(paths), 12)


if __name__ == '__main__':
    unittest.main()
