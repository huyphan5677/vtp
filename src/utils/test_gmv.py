import pandas as pd
import numpy as np


# =====================================================
# CODE CŨ
# =====================================================

def compute_gmv_old(df, months_window):

    df = df.copy()

    df["month"] = pd.to_datetime(
        df["month"],
        format="%Y%m"
    ).dt.to_period("M")


    max_month = df["month"].max()
    min_month = max_month - months_window + 1

    df = df[
        df["month"].between(
            min_month,
            max_month
        )
    ]


    agg_df = df.groupby("cus_id").agg(
        thu_ho=("thu_ho","sum"),
        thuho_tongdon=("thuho_tongdon","sum"),
        don_ptc_cod=("don_ptc_cod","sum"),
        tongdon_cod=("tongdon_cod","sum"),
        don_ptc=("don_ptc","sum"),
        tong_tien=("tong_tien","sum"),
        tong_don=("tong_don","sum"),
        tong_cuoc_ptc=("tong_cuoc_ptc","sum")
    ).reset_index()


    group_cod = agg_df[
        (agg_df["thu_ho"] > 0)
        |
        (agg_df["thuho_tongdon"] > 0)
    ].copy()


    group_non_cod = agg_df[
        (agg_df["thu_ho"] <= 0)
        &
        (agg_df["thuho_tongdon"] <= 0)
    ].copy()



    group_cod["avg_don"] = np.where(
        group_cod["thu_ho"] > 0,

        group_cod["thu_ho"]
        /
        group_cod["don_ptc_cod"].replace(0,np.nan),

        group_cod["thuho_tongdon"]
        /
        group_cod["tongdon_cod"].replace(0,np.nan)
    )


    group_cod["gmv"] = (
        group_cod["don_ptc"]
        *
        group_cod["avg_don"]
    )


    ship_rev = (
        group_cod["don_ptc"]
        *
        group_cod["tong_tien"]
        /
        group_cod["tong_don"].replace(0,np.nan)
    )


    group_cod["ship_rev_ratio"] = np.where(
        group_cod["tong_cuoc_ptc"] > 0,

        group_cod["tong_cuoc_ptc"]
        /
        group_cod["gmv"],

        ship_rev
        /
        group_cod["gmv"]
    )


    med_ratio = group_cod["ship_rev_ratio"].median()



    ship_rev_non = (
        group_non_cod["don_ptc"]
        *
        group_non_cod["tong_tien"]
        /
        group_non_cod["tong_don"].replace(0,np.nan)
    )


    group_non_cod["gmv"] = np.where(

        group_non_cod["tong_cuoc_ptc"] > 0,

        group_non_cod["tong_cuoc_ptc"]
        /
        med_ratio,

        ship_rev_non
        /
        med_ratio
    )


    result = pd.concat(
        [
            group_cod[["cus_id","gmv"]],
            group_non_cod[["cus_id","gmv"]]
        ]
    )


    result["gmv"] = (
        result["gmv"]
        .fillna(0)
        .div(1_000_000)
        .clip(1,9999)
    )


    return result.sort_values("cus_id").reset_index(drop=True)



# =====================================================
# CODE MỚI
# =====================================================

def compute_gmv_new(df, months_window):

    df = df.copy()

    df["month"] = pd.to_datetime(
        df["month"],
        format="%Y%m"
    ).dt.to_period("M")


    max_month = df["month"].max()

    min_month = (
        max_month
        -
        months_window
        +
        1
    )

    df = df[
        df["month"].between(
            min_month,
            max_month
        )
    ]

    agg_df = (
        df
        .groupby(
            "cus_id",
            as_index=False
        )
        .agg(
            {
                "count":"sum",
                "value":"sum",
                "tong_don":"sum",
                "thu_ho":"sum",
                "tong_cuoc_ptc":"sum",
                "don_ptc_cod":"sum",
                "thuho_tongdon":"sum",
                "tongdon_cod":"sum"
            }
        )
    )

    ship_rev = (
        agg_df["count"]
        *
        agg_df["value"]
        /
        agg_df["tong_don"].replace(0,np.nan)
    )

    cod_mask = (
        (agg_df["thu_ho"] > 0)
        |
        (agg_df["thuho_tongdon"] > 0)
    )

    avg_don = np.where(

        agg_df["thu_ho"] > 0,

        agg_df["thu_ho"]
        /
        agg_df["don_ptc_cod"].replace(0,np.nan),

        agg_df["thuho_tongdon"]
        /
        agg_df["tongdon_cod"].replace(0,np.nan)

    )

    gmv_cod = (
        agg_df["count"]
        *
        avg_don
    )

    ship_rev_ratio = np.where(

        agg_df["tong_cuoc_ptc"] > 0,

        agg_df["tong_cuoc_ptc"]
        /
        gmv_cod,

        ship_rev
        /
        gmv_cod

    )

    med_ratio = np.nanmedian(
        ship_rev_ratio[cod_mask]
    )


    if np.isnan(med_ratio):
        med_ratio = 1.0

    gmv_non = np.where(

        agg_df["tong_cuoc_ptc"] > 0,

        agg_df["tong_cuoc_ptc"]
        /
        med_ratio,

        ship_rev
        /
        med_ratio

    )

    agg_df["gmv"] = np.where(
        cod_mask,
        gmv_cod,
        gmv_non
    )


    result = agg_df[
        [
            "cus_id",
            "gmv"
        ]
    ]


    result["gmv"] = (
        result["gmv"]
        .fillna(0)
        .div(1_000_000)
        .clip(1,9999)
    )


    return result.sort_values(
        "cus_id"
    ).reset_index(drop=True)

# =====================================================
# DATA TEST
# =====================================================


df = pd.DataFrame({

    "cus_id":[
        1,1,
        2,2,
        3,3,
        4,4
    ],

    "month":[
        "202501",
        "202502",
        "202501",
        "202502",
        "202501",
        "202502",
        "202501",
        "202502"
    ],


    # code mới dùng count
    "count":[
        100,120,
        50,60,
        80,90,
        70,80
    ],


    # code mới dùng value
    "value":[
        200000,
        220000,
        300000,
        320000,
        150000,
        170000,
        250000,
        260000
    ],

    # code cũ dùng
    "don_ptc":[
        100,120,
        50,60,
        80,90,
        70,80
    ],

    "tong_tien":[
        200000,
        220000,
        300000,
        320000,
        150000,
        170000,
        250000,
        260000
    ],

    "tong_don":[
        120,140,
        60,70,
        100,110,
        90,100
    ],

    # COD user 1,3
    "thu_ho":[
        10000000,
        12000000,
        0,
        0,
        15000000,
        16000000,
        0,
        0
    ],

    "thuho_tongdon":[
        0,0,
        0,0,
        0,0,
        0,0
    ],


    "don_ptc_cod":[
        100,120,
        0,0,
        80,90,
        0,0
    ],

    "tongdon_cod":[
        100,120,
        0,0,
        80,90,
        0,0
    ],

    "tong_cuoc_ptc":[
        5000000,
        6000000,
        3000000,
        3500000,
        4000000,
        4500000,
        5000000,
        5500000
    ]

})


# convert cho code mới

df_new = df.copy()

df_new["count"] = df_new["don_ptc"]

df_new["value"] = df_new["tong_tien"]



# =====================================================
# RUN TEST
# =====================================================

old_result = compute_gmv_old(
    df,
    2
)


new_result = compute_gmv_new(
    df_new,
    2
)



print("\n===== OLD RESULT =====")
print(old_result)


print("\n===== NEW RESULT =====")
print(new_result)



compare = old_result.merge(
    new_result,
    on="cus_id",
    suffixes=("_old","_new")
)


compare["diff"] = (
    compare["gmv_new"]
    -
    compare["gmv_old"]
)


print("\n===== COMPARE =====")
print(compare)



print("\n===== CHECK =====")

if np.allclose(
    compare["diff"],
    0
):
    print("PASS: Hai logic cho kết quả giống nhau")
else:
    print("FAIL: Có khác biệt")