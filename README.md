# Snowflake Dashboard with Streamlit

این پروژه یک داشبورد ساده با **Streamlit** است که داده‌ها را از **Snowflake** می‌گیرد و به صورت چارت نمایش می‌دهد.

## اجرا به صورت محلی
1. پکیج‌ها را نصب کنید:
    ```
    pip install -r requirements.txt
    ```
2. اطلاعات Snowflake را در `.streamlit/secrets.toml` قرار دهید.
3. داشبورد را اجرا کنید:
    ```
    streamlit run dashboard.py
    ```

## دیپلوی روی Streamlit Cloud
1. این ریپازیتوری را به GitHub اضافه کنید.
2. به [share.streamlit.io](https://share.streamlit.io) بروید و ریپازیتوری را وصل کنید.
3. Secrets را در تنظیمات Streamlit Cloud اضافه کنید.
