def generate_amount_in_words(amount, currency):
    if amount == 0:
        return f"Zero {currency}"
    
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine']
    teens = ['Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen',
             'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    thousands = ['', 'Thousand', 'Million', 'Billion']

    def convert_below_thousand(n):
        if n == 0:
            return ''
        elif n < 10:
            return ones[n]
        elif n < 20:
            return teens[n - 10]
        elif n < 100:
            return tens[n // 10] + (' ' + ones[n % 10] if n % 10 != 0 else '')
        else:
            return ones[n // 100] + ' Hundred' + (' ' + convert_below_thousand(n % 100) if n % 100 != 0 else '')

    # FIXED chunking logic
    num_str = str(amount)[::-1]
    chunks = [num_str[i:i+3][::-1] for i in range(0, len(num_str), 3)]

    result = []
    for i, chunk in enumerate(chunks):
        num = int(chunk)
        if num != 0:
            result.append(convert_below_thousand(num) + ' ' + thousands[i])

    words = ' '.join(reversed(result)).strip()
    return f"{words} {currency} ({amount} {currency}) excluding VAT"


print(generate_amount_in_words(3850, "MRU"))
